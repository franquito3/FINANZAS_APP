import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../../config/app_config.dart';

class SummaryCardsWidget extends StatelessWidget {
  final double allTimeBalance;
  final double monthlyIncome;
  final double monthlyExpense;
  final int pendingCount;
  final String monthLabel;

  const SummaryCardsWidget({
    super.key,
    required this.allTimeBalance,
    required this.monthlyIncome,
    required this.monthlyExpense,
    required this.pendingCount,
    required this.monthLabel,
  });

  String _formatAmount(double value) {
    final fmt = NumberFormat('#,##0.00', 'en_US');
    return '${AppConfig.currencySymbol} ${fmt.format(value)}';
  }

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    final monthlyNet = monthlyIncome - monthlyExpense;
    final netPrefix = monthlyNet >= 0 ? '+' : '';
    final syncText = pendingCount > 0
        ? '$pendingCount pendiente(s) de sincronizar'
        : 'Respaldado en la nube';

    return Column(
      children: [
        // Tarjeta Principal: Saldo Disponible Total
        Container(
          width: double.infinity,
          padding: const EdgeInsets.all(18),
          decoration: BoxDecoration(
            gradient: LinearGradient(
              colors: [
                colorScheme.primaryContainer,
                colorScheme.secondaryContainer.withOpacity(0.85),
              ],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
            borderRadius: BorderRadius.circular(20),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Expanded(
                    child: Text(
                      'Saldo Disponible Total',
                      style: TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.w600,
                        color: colorScheme.onPrimaryContainer.withOpacity(0.85),
                      ),
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                    decoration: BoxDecoration(
                      color: colorScheme.surface.withOpacity(0.65),
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(
                          pendingCount > 0 ? Icons.cloud_upload_outlined : Icons.cloud_done_rounded,
                          size: 14,
                          color: pendingCount > 0 ? Colors.amber : const Color(0xFF10B981),
                        ),
                        const SizedBox(width: 5),
                        Text(
                          syncText,
                          style: TextStyle(
                            fontSize: 11,
                            fontWeight: FontWeight.w600,
                            color: colorScheme.onSurface,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              FittedBox(
                fit: BoxFit.scaleDown,
                alignment: Alignment.centerLeft,
                child: Text(
                  _formatAmount(allTimeBalance),
                  style: TextStyle(
                    fontSize: 28,
                    fontWeight: FontWeight.w800,
                    color: colorScheme.onPrimaryContainer,
                  ),
                ),
              ),
              const SizedBox(height: 6),
              Text(
                'Balance neto $monthLabel: $netPrefix${_formatAmount(monthlyNet)}',
                style: TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w500,
                  color: colorScheme.onPrimaryContainer.withOpacity(0.8),
                ),
                overflow: TextOverflow.ellipsis,
              ),
            ],
          ),
        ),
        const SizedBox(height: 12),
        // Fila de Ingresos y Gastos del Mes
        Row(
          children: [
            Expanded(
              child: _buildMetricCard(
                context: context,
                title: 'Ingresos ($monthLabel)',
                amount: _formatAmount(monthlyIncome),
                icon: Icons.trending_up_rounded,
                accentColor: const Color(0xFF2DD4BF),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: _buildMetricCard(
                context: context,
                title: 'Gastos ($monthLabel)',
                amount: _formatAmount(monthlyExpense),
                icon: Icons.trending_down_rounded,
                accentColor: const Color(0xFFF87171),
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildMetricCard({
    required BuildContext context,
    required String title,
    required String amount,
    required IconData icon,
    required Color accentColor,
  }) {
    final colorScheme = Theme.of(context).colorScheme;
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: colorScheme.surfaceContainerHighest.withOpacity(0.55),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: colorScheme.outlineVariant.withOpacity(0.4)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(6),
                decoration: BoxDecoration(
                  color: accentColor.withOpacity(0.15),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Icon(icon, color: accentColor, size: 18),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  title,
                  style: TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                    color: colorScheme.onSurfaceVariant,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          FittedBox(
            fit: BoxFit.scaleDown,
            alignment: Alignment.centerLeft,
            child: Text(
              amount,
              style: TextStyle(
                fontSize: 19,
                fontWeight: FontWeight.bold,
                color: colorScheme.onSurface,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
