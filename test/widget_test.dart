import 'package:flutter_test/flutter_test.dart';
import 'package:mis_finanzas/config/app_config.dart';
import 'package:mis_finanzas/models/transaction_model.dart';

void main() {
  test('TransactionModel serializa y extrae metodo de pago correctamente', () {
    final note = TransactionModel.formatNoteWithPayment('Yape / Plin', 'Almuerzo ejecutivo');
    final tx = TransactionModel(
      id: 'tx-1',
      userId: 'local_user',
      type: 'gasto',
      amount: 25.50,
      category: 'Alimentación',
      note: note,
      createdAt: DateTime(2026, 10, 16),
      synced: false,
    );

    expect(tx.isExpense, isTrue);
    expect(tx.paymentMethod, equals('Yape / Plin'));
    expect(tx.cleanNote, equals('Almuerzo ejecutivo'));
    expect(AppConfig.getCategoryMeta(tx.category).group, equals('Necesidades (50%)'));
  });
}
