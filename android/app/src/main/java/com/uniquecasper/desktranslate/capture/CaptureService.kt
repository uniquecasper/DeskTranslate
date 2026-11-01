package com.uniquecasper.desktranslate.capture

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Context
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.PixelFormat
import android.hardware.display.DisplayManager
import android.hardware.display.VirtualDisplay
import android.media.Image
import android.media.ImageReader
import android.media.projection.MediaProjection
import android.media.projection.MediaProjectionManager
import android.os.Build
import android.os.Handler
import android.os.HandlerThread
import android.os.IBinder
import android.os.SystemClock
import android.util.DisplayMetrics
import android.view.WindowManager
import com.uniquecasper.desktranslate.ocr.OcrEngine
import java.util.concurrent.Executors
import java.util.concurrent.atomic.AtomicBoolean

class CaptureService : Service() {
    private var projection: MediaProjection? = null
    private var virtualDisplay: VirtualDisplay? = null
    private var imageReader: ImageReader? = null
    private var imageThread: HandlerThread? = null
    private var imageHandler: Handler? = null
    private var ocr: OcrEngine? = null
    private val worker = Executors.newSingleThreadExecutor()
    private val processing = AtomicBoolean(false)
    private var lastFrameAt = 0L
    private var script = "Latin"

    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
        ocr = OcrEngine()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_STOP -> {
                stopCapture()
                stopSelf()
                return START_NOT_STICKY
            }
            ACTION_START -> {
                startCaptureForeground()
                val resultCode = intent.getIntExtra(EXTRA_RESULT_CODE, 0)
                val data = if (Build.VERSION.SDK_INT >= 33) {
                    intent.getParcelableExtra(EXTRA_RESULT_DATA, Intent::class.java)
                } else {
                    @Suppress("DEPRECATION")
                    intent.getParcelableExtra(EXTRA_RESULT_DATA)
                }
                script = intent.getStringExtra(EXTRA_SCRIPT) ?: "Latin"
                if (data == null) {
                    publishStatus("Screen capture permission data was missing.")
                    stopSelf()
                    return START_NOT_STICKY
                }
                try {
                    beginProjection(resultCode, data)
                } catch (error: Exception) {
                    publishStatus("Could not start screen capture: " + error.javaClass.simpleName)
                    stopCapture()
                    stopSelf()
                }
            }
        }
        return START_NOT_STICKY
    }

    private fun startCaptureForeground() {
        val notification = Notification.Builder(this, CHANNEL_ID)
            .setSmallIcon(android.R.drawable.ic_menu_view)
            .setContentTitle("DeskTranslate is capturing")
            .setContentText("Screen text recognition is active. Stop it from DeskTranslate.")
            .setOngoing(true)
            .build()

        if (Build.VERSION.SDK_INT >= 29) {
            startForeground(
                NOTIFICATION_ID,
                notification,
                android.content.pm.ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PROJECTION
            )
        } else {
            startForeground(NOTIFICATION_ID, notification)
        }
    }

    private fun beginProjection(resultCode: Int, data: Intent) {
        val manager = getSystemService(Context.MEDIA_PROJECTION_SERVICE) as MediaProjectionManager
        val activeProjection = manager.getMediaProjection(resultCode, data)
            ?: throw IllegalStateException("Android did not grant a media projection")
        projection = activeProjection

        activeProjection.registerCallback(object : MediaProjection.Callback() {
            override fun onStop() {
                stopCapture()
                stopSelf()
            }
        }, Handler(mainLooper))

        val metrics = DisplayMetrics()
        @Suppress("DEPRECATION")
        (getSystemService(Context.WINDOW_SERVICE) as WindowManager).defaultDisplay.getRealMetrics(metrics)
        val width = metrics.widthPixels
        val height = metrics.heightPixels
        val density = metrics.densityDpi
        require(width > 0 && height > 0 && width.toLong() * height.toLong() <= 16_000_000L) {
            "Display dimensions are outside the supported capture limit"
        }

        imageThread = HandlerThread("DeskTranslateFrames").also { it.start() }
        imageHandler = Handler(imageThread!!.looper)
        val reader = ImageReader.newInstance(width, height, PixelFormat.RGBA_8888, 2)
        imageReader = reader
        reader.setOnImageAvailableListener({ source -> processLatestFrame(source) }, imageHandler)

        virtualDisplay = activeProjection.createVirtualDisplay(
            "DeskTranslate",
            width,
            height,
            density,
            DisplayManager.VIRTUAL_DISPLAY_FLAG_AUTO_MIRROR,
            reader.surface,
            null,
            imageHandler
        ) ?: throw IllegalStateException("Could not create the screen capture display")
        publishStatus("Screen capture is active. Select Stop when finished.")
    }

    private fun processLatestFrame(source: ImageReader) {
        val now = SystemClock.elapsedRealtime()
        if (now - lastFrameAt < FRAME_INTERVAL_MS || !processing.compareAndSet(false, true)) {
            source.acquireLatestImage()?.close()
            return
        }
        lastFrameAt = now
        val image = source.acquireLatestImage()
        if (image == null) {
            processing.set(false)
            return
        }

        val bitmap = try {
            imageToBitmap(image)
        } catch (_: Exception) {
            null
        } finally {
            image.close()
        }

        if (bitmap == null) {
            processing.set(false)
            return
        }

        worker.execute {
            try {
                val recognized = ocr?.recognize(bitmap, script).orEmpty()
                if (recognized.isNotBlank()) {
                    sendBroadcast(
                        Intent(ACTION_OCR_RESULT)
                            .setPackage(packageName)
                            .putExtra(EXTRA_TEXT, recognized.take(MAX_TEXT_CHARS))
                    )
                }
            } catch (error: Exception) {
                publishStatus("OCR failed: " + error.javaClass.simpleName)
            } finally {
                bitmap.recycle()
                processing.set(false)
            }
        }
    }

    private fun imageToBitmap(image: Image): Bitmap {
        val plane = image.planes.first()
        val pixelStride = plane.pixelStride
        val paddedWidth = plane.rowStride / pixelStride
        val padded = Bitmap.createBitmap(paddedWidth, image.height, Bitmap.Config.ARGB_8888)
        padded.copyPixelsFromBuffer(plane.buffer)
        if (paddedWidth == image.width) return padded
        val cropped = Bitmap.createBitmap(padded, 0, 0, image.width, image.height)
        padded.recycle()
        return cropped
    }

    private fun publishStatus(message: String) {
        sendBroadcast(
            Intent(ACTION_CAPTURE_STATUS)
                .setPackage(packageName)
                .putExtra(EXTRA_TEXT, message.take(300))
        )
    }

    private fun stopCapture() {
        virtualDisplay?.release()
        virtualDisplay = null
        imageReader?.setOnImageAvailableListener(null, null)
        imageReader?.close()
        imageReader = null
        imageThread?.quitSafely()
        imageThread = null
        imageHandler = null
        val oldProjection = projection
        projection = null
        oldProjection?.stop()
        processing.set(false)
        stopForeground(STOP_FOREGROUND_REMOVE)
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= 26) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "Screen capture",
                NotificationManager.IMPORTANCE_LOW
            )
            getSystemService(NotificationManager::class.java).createNotificationChannel(channel)
        }
    }

    override fun onDestroy() {
        stopCapture()
        worker.shutdownNow()
        ocr?.close()
        ocr = null
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    companion object {
        const val ACTION_START = "com.uniquecasper.desktranslate.capture.START"
        const val ACTION_STOP = "com.uniquecasper.desktranslate.capture.STOP"
        const val ACTION_OCR_RESULT = "com.uniquecasper.desktranslate.capture.OCR_RESULT"
        const val ACTION_CAPTURE_STATUS = "com.uniquecasper.desktranslate.capture.STATUS"
        const val EXTRA_RESULT_CODE = "result_code"
        const val EXTRA_RESULT_DATA = "result_data"
        const val EXTRA_SCRIPT = "script"
        const val EXTRA_TEXT = "text"
        private const val CHANNEL_ID = "desktranslate_capture"
        private const val NOTIFICATION_ID = 4102
        private const val FRAME_INTERVAL_MS = 800L
        private const val MAX_TEXT_CHARS = 12000
    }
}
