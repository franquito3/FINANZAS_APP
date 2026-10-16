import '../config/app_config.dart';

class TransactionModel {
  final String id;
  final String userId;
  final String type; // 'gasto' | 'ingreso'
  final double amount;
  final String category;
  final String note;
  final DateTime createdAt;
  final bool synced;

  const TransactionModel({
    required this.id,
    required this.userId,
    required this.type,
    required this.amount,
    required this.category,
    required this.note,
    required this.createdAt,
    required this.synced,
  });

  bool get isExpense => type == 'gasto';

  /// Extrae el método de pago codificado al inicio de la nota '[Método] Detalle'
  String get paymentMethod {
    final trimmed = note.trim();
    if (trimmed.startsWith('[') && trimmed.contains(']')) {
      final idx = trimmed.indexOf(']');
      final candidate = trimmed.substring(1, idx).trim();
      if (AppConfig.paymentMethods.contains(candidate)) {
        return candidate;
      }
    }
    return AppConfig.paymentMethods.first;
  }

  /// Devuelve la nota limpia sin el prefijo '[Método]'
  String get cleanNote {
    final trimmed = note.trim();
    if (trimmed.startsWith('[') && trimmed.contains(']')) {
      final idx = trimmed.indexOf(']');
      final candidate = trimmed.substring(1, idx).trim();
      if (AppConfig.paymentMethods.contains(candidate)) {
        return trimmed.substring(idx + 1).trim();
      }
    }
    return trimmed;
  }

  static String formatNoteWithPayment(String method, String rawNote) {
    final clean = rawNote.trim();
    final m = method.trim().isEmpty ? AppConfig.paymentMethods.first : method.trim();
    if (clean.isEmpty) {
      return '[$m]';
    }
    final combined = '[$m] $clean';
    return combined.length > 90 ? combined.substring(0, 90) : combined;
  }

  TransactionModel copyWith({
    String? id,
    String? userId,
    String? type,
    double? amount,
    String? category,
    String? note,
    DateTime? createdAt,
    bool? synced,
  }) {
    return TransactionModel(
      id: id ?? this.id,
      userId: userId ?? this.userId,
      type: type ?? this.type,
      amount: amount ?? this.amount,
      category: category ?? this.category,
      note: note ?? this.note,
      createdAt: createdAt ?? this.createdAt,
      synced: synced ?? this.synced,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'user_id': userId,
      'type': type,
      'amount': double.parse(amount.toStringAsFixed(2)),
      'category': category,
      'note': note,
      'created_at': createdAt.toIso8601String(),
      'synced': synced,
    };
  }

  Map<String, dynamic> toSupabasePayload(String currentUserId) {
    return {
      'id': id,
      'user_id': currentUserId,
      'type': type,
      'amount': double.parse(amount.toStringAsFixed(2)),
      'category': category,
      'note': note,
      'created_at': createdAt.toIso8601String(),
    };
  }

  factory TransactionModel.fromJson(Map<String, dynamic> json, {bool? forceSynced}) {
    DateTime parsedDate;
    try {
      parsedDate = DateTime.parse(json['created_at'].toString()).toLocal();
    } catch (_) {
      parsedDate = DateTime.now();
    }

    return TransactionModel(
      id: json['id']?.toString() ?? '',
      userId: json['user_id']?.toString() ?? 'local_user',
      type: json['type']?.toString() == 'ingreso' ? 'ingreso' : 'gasto',
      amount: (json['amount'] is num)
          ? (json['amount'] as num).toDouble()
          : double.tryParse(json['amount']?.toString() ?? '0') ?? 0.0,
      category: json['category']?.toString() ?? 'Alimentación',
      note: json['note']?.toString() ?? '',
      createdAt: parsedDate,
      synced: forceSynced ?? (json['synced'] == true),
    );
  }
}
