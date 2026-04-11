import 'dart:convert';
import 'package:sqflite/sqflite.dart';
import 'package:path/path.dart' as p;
import '../config/api_config.dart';
import '../models/transaction.dart';
import '../models/prediction.dart';

/// Local SQLite storage service for offline caching of transactions and predictions
class StorageService {
  static StorageService? _instance;
  Database? _db;

  StorageService._internal();

  factory StorageService() {
    _instance ??= StorageService._internal();
    return _instance!;
  }

  // ---------------------------------------------------------------------------
  // Initialisation
  // ---------------------------------------------------------------------------

  Future<void> init() async {
    if (_db != null) return;
    final dbPath = p.join(await getDatabasesPath(), ApiConfig.dbName);
    _db = await openDatabase(
      dbPath,
      version: ApiConfig.dbVersion,
      onCreate: _onCreate,
      onUpgrade: _onUpgrade,
    );
  }

  Future<void> _onCreate(Database db, int version) async {
    await db.execute('''
      CREATE TABLE transactions (
        id TEXT PRIMARY KEY,
        payee_vpa TEXT NOT NULL,
        payee_name TEXT NOT NULL,
        amount REAL NOT NULL,
        currency TEXT NOT NULL DEFAULT 'INR',
        timestamp TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',
        note TEXT,
        device_id TEXT,
        latitude REAL,
        longitude REAL,
        is_synced INTEGER NOT NULL DEFAULT 0
      )
    ''');

    await db.execute('''
      CREATE TABLE predictions (
        transaction_id TEXT PRIMARY KEY,
        risk_score REAL NOT NULL,
        risk_level TEXT NOT NULL,
        verdict TEXT NOT NULL,
        layer_scores TEXT NOT NULL,
        ensemble_votes TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        is_cached INTEGER NOT NULL DEFAULT 0,
        session_id TEXT,
        FOREIGN KEY (transaction_id) REFERENCES transactions(id) ON DELETE CASCADE
      )
    ''');

    await db.execute('''
      CREATE INDEX idx_transactions_timestamp ON transactions(timestamp DESC)
    ''');
    await db.execute('''
      CREATE INDEX idx_predictions_timestamp ON predictions(timestamp DESC)
    ''');
  }

  Future<void> _onUpgrade(Database db, int oldVersion, int newVersion) async {
    // Future migration logic
  }

  // ---------------------------------------------------------------------------
  // Transactions
  // ---------------------------------------------------------------------------

  Future<void> saveTransaction(Transaction txn) async {
    await _db!.insert(
      'transactions',
      _transactionToRow(txn),
      conflictAlgorithm: ConflictAlgorithm.replace,
    );
  }

  Future<void> saveTransactions(List<Transaction> txns) async {
    final batch = _db!.batch();
    for (final t in txns) {
      batch.insert('transactions', _transactionToRow(t),
          conflictAlgorithm: ConflictAlgorithm.replace);
    }
    await batch.commit(noResult: true);
  }

  Future<Transaction?> getTransaction(String id) async {
    final rows = await _db!.query(
      'transactions',
      where: 'id = ?',
      whereArgs: [id],
      limit: 1,
    );
    if (rows.isEmpty) return null;
    return _transactionFromRow(rows.first);
  }

  Future<List<Transaction>> getTransactions({
    int? limit,
    int? offset,
    String? search,
    String? status,
    DateTime? fromDate,
    DateTime? toDate,
  }) async {
    final where = <String>[];
    final args = <dynamic>[];

    if (search != null && search.isNotEmpty) {
      where.add('(payee_vpa LIKE ? OR payee_name LIKE ?)');
      args.addAll(['%$search%', '%$search%']);
    }
    if (status != null) {
      where.add('status = ?');
      args.add(status);
    }
    if (fromDate != null) {
      where.add('timestamp >= ?');
      args.add(fromDate.toIso8601String());
    }
    if (toDate != null) {
      where.add('timestamp <= ?');
      args.add(toDate.toIso8601String());
    }

    final rows = await _db!.query(
      'transactions',
      where: where.isEmpty ? null : where.join(' AND '),
      whereArgs: args.isEmpty ? null : args,
      orderBy: 'timestamp DESC',
      limit: limit,
      offset: offset,
    );
    return rows.map(_transactionFromRow).toList();
  }

  Future<int> getTransactionCount() async {
    final result =
        await _db!.rawQuery('SELECT COUNT(*) as count FROM transactions');
    return result.first['count'] as int;
  }

  Future<void> deleteTransaction(String id) async {
    await _db!.delete('transactions', where: 'id = ?', whereArgs: [id]);
  }

  // ---------------------------------------------------------------------------
  // Predictions
  // ---------------------------------------------------------------------------

  Future<void> savePrediction(Prediction prediction) async {
    await _db!.insert(
      'predictions',
      _predictionToRow(prediction),
      conflictAlgorithm: ConflictAlgorithm.replace,
    );
  }

  Future<Prediction?> getPrediction(String transactionId) async {
    final rows = await _db!.query(
      'predictions',
      where: 'transaction_id = ?',
      whereArgs: [transactionId],
      limit: 1,
    );
    if (rows.isEmpty) return null;
    return _predictionFromRow(rows.first);
  }

  Future<List<Prediction>> getPredictions({int? limit, int? offset}) async {
    final rows = await _db!.query(
      'predictions',
      orderBy: 'timestamp DESC',
      limit: limit,
      offset: offset,
    );
    return rows.map(_predictionFromRow).toList();
  }

  // ---------------------------------------------------------------------------
  // Stats (computed from local DB)
  // ---------------------------------------------------------------------------

  Future<Map<String, dynamic>> getLocalStats() async {
    final total = await _db!
        .rawQuery('SELECT COUNT(*) as count FROM predictions');
    final fraud = await _db!
        .rawQuery("SELECT COUNT(*) as count FROM predictions WHERE risk_level='fraud'");
    final suspicious = await _db!.rawQuery(
        "SELECT COUNT(*) as count FROM predictions WHERE risk_level='suspicious'");
    final safe = await _db!
        .rawQuery("SELECT COUNT(*) as count FROM predictions WHERE risk_level='safe'");
    final avg = await _db!
        .rawQuery('SELECT AVG(risk_score) as avg FROM predictions');

    final totalCount = total.first['count'] as int;
    final fraudCount = fraud.first['count'] as int;
    final avgScore = (avg.first['avg'] as num?)?.toDouble() ?? 0.0;

    return {
      'total_predictions': totalCount,
      'fraud_count': fraudCount,
      'suspicious_count': suspicious.first['count'] as int,
      'safe_count': safe.first['count'] as int,
      'average_risk_score': avgScore,
      'fraud_rate': totalCount > 0 ? fraudCount / totalCount : 0.0,
    };
  }

  // ---------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------

  Map<String, dynamic> _transactionToRow(Transaction t) => {
        'id': t.id,
        'payee_vpa': t.payeeVpa,
        'payee_name': t.payeeName,
        'amount': t.amount,
        'currency': t.currency,
        'timestamp': t.timestamp.toIso8601String(),
        'status': t.status.name,
        'note': t.note,
        'device_id': t.deviceId,
        'latitude': t.latitude,
        'longitude': t.longitude,
        'is_synced': t.isSynced ? 1 : 0,
      };

  Transaction _transactionFromRow(Map<String, dynamic> row) => Transaction(
        id: row['id'] as String,
        payeeVpa: row['payee_vpa'] as String,
        payeeName: row['payee_name'] as String,
        amount: row['amount'] as double,
        currency: row['currency'] as String? ?? 'INR',
        timestamp: DateTime.parse(row['timestamp'] as String),
        status: TransactionStatus.values.firstWhere(
          (s) => s.name == row['status'],
          orElse: () => TransactionStatus.pending,
        ),
        note: row['note'] as String?,
        deviceId: row['device_id'] as String?,
        latitude: row['latitude'] as double?,
        longitude: row['longitude'] as double?,
        isSynced: (row['is_synced'] as int?) == 1,
      );

  Map<String, dynamic> _predictionToRow(Prediction p) => {
        'transaction_id': p.transactionId,
        'risk_score': p.riskScore,
        'risk_level': p.riskLevel.name,
        'verdict': p.verdict,
        'layer_scores': jsonEncode(p.layerScores.map((l) => l.toJson()).toList()),
        'ensemble_votes':
            jsonEncode(p.ensembleVotes.map((v) => v.toJson()).toList()),
        'timestamp': p.timestamp.toIso8601String(),
        'is_cached': p.isCached ? 1 : 0,
        'session_id': p.sessionId,
      };

  Prediction _predictionFromRow(Map<String, dynamic> row) {
    final layerScores = (jsonDecode(row['layer_scores'] as String) as List)
        .map((e) => LayerScore.fromJson(e as Map<String, dynamic>))
        .toList();
    final votes = (jsonDecode(row['ensemble_votes'] as String) as List)
        .map((e) => EnsembleVote.fromJson(e as Map<String, dynamic>))
        .toList();
    final riskLevel = RiskLevel.values.firstWhere(
      (l) => l.name == row['risk_level'],
      orElse: () => RiskLevel.safe,
    );
    return Prediction(
      transactionId: row['transaction_id'] as String,
      riskScore: row['risk_score'] as double,
      riskLevel: riskLevel,
      verdict: row['verdict'] as String,
      layerScores: layerScores,
      ensembleVotes: votes,
      timestamp: DateTime.parse(row['timestamp'] as String),
      isCached: (row['is_cached'] as int?) == 1,
      sessionId: row['session_id'] as String?,
    );
  }

  Future<void> close() async {
    await _db?.close();
    _db = null;
  }
}
