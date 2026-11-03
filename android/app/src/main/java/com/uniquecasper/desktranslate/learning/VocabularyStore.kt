package com.uniquecasper.desktranslate.learning

import android.content.ContentValues
import android.content.Context
import android.database.sqlite.SQLiteDatabase
import android.database.sqlite.SQLiteOpenHelper

data class VocabularyEntry(
    val id: Long,
    val source: String,
    val translation: String,
    val sourceLanguage: String,
    val targetLanguage: String,
    val createdAt: Long
)

class VocabularyStore(context: Context) :
    SQLiteOpenHelper(context, "desktranslate-vocabulary.db", null, DATABASE_VERSION) {

    override fun onCreate(db: SQLiteDatabase) {
        db.execSQL(
            "CREATE TABLE vocabulary (" +
                "id INTEGER PRIMARY KEY AUTOINCREMENT, " +
                "source TEXT NOT NULL CHECK(length(source) BETWEEN 1 AND 500), " +
                "translation TEXT NOT NULL CHECK(length(translation) BETWEEN 1 AND 1000), " +
                "source_language TEXT NOT NULL, target_language TEXT NOT NULL, " +
                "created_at INTEGER NOT NULL)"
        )
        db.execSQL("CREATE INDEX vocabulary_pair_created ON vocabulary(source_language, target_language, created_at DESC)")
    }

    override fun onUpgrade(db: SQLiteDatabase, oldVersion: Int, newVersion: Int) {
        throw IllegalStateException("Unsupported vocabulary database upgrade: " + oldVersion + " -> " + newVersion)
    }

    fun save(source: String, translation: String, sourceLanguage: String, targetLanguage: String): Long {
        val cleanSource = source.trim()
        val cleanTranslation = translation.trim()
        require(cleanSource.isNotEmpty() && cleanSource.length <= 500)
        require(cleanTranslation.isNotEmpty() && cleanTranslation.length <= 1000)
        require(sourceLanguage.length in 2..20 && targetLanguage.length in 2..20)
        val db = writableDatabase
        db.beginTransaction()
        try {
            val values = ContentValues().apply {
                put("source", cleanSource)
                put("translation", cleanTranslation)
                put("source_language", sourceLanguage)
                put("target_language", targetLanguage)
                put("created_at", System.currentTimeMillis())
            }
            val id = db.insertOrThrow("vocabulary", null, values)
            db.execSQL(
                "DELETE FROM vocabulary WHERE id NOT IN " +
                    "(SELECT id FROM vocabulary ORDER BY id DESC LIMIT " + MAX_ENTRIES + ")"
            )
            db.setTransactionSuccessful()
            return id
        } finally {
            db.endTransaction()
        }
    }

    fun recent(limit: Int = 100): List<VocabularyEntry> {
        require(limit in 1..500)
        val result = mutableListOf<VocabularyEntry>()
        readableDatabase.query(
            "vocabulary",
            arrayOf("id", "source", "translation", "source_language", "target_language", "created_at"),
            null,
            null,
            null,
            null,
            "created_at DESC, id DESC",
            limit.toString()
        ).use { cursor ->
            while (cursor.moveToNext()) {
                result += VocabularyEntry(
                    cursor.getLong(0),
                    cursor.getString(1),
                    cursor.getString(2),
                    cursor.getString(3),
                    cursor.getString(4),
                    cursor.getLong(5)
                )
            }
        }
        return result
    }

    fun delete(id: Long): Int {
        require(id > 0)
        return writableDatabase.delete("vocabulary", "id = ?", arrayOf(id.toString()))
    }

    companion object {
        private const val DATABASE_VERSION = 1
        private const val MAX_ENTRIES = 10000
    }
}
