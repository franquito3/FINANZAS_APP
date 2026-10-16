import 'dart:math';
import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../../config/app_config.dart';
import '../../models/transaction_model.dart';

class Budget503020Card extends StatelessWidget {
  final List<TransactionModel> transactions;
  final double monthlyIncome;

  const Budget503020Card({
    super.key,
    required this.transactions,
    required this.monthlyIncome,
  });

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    final fmt = NumberFormat('#,##0.00', 'en_US');

    final Map<String, double> spentByGroup = {
      'Necesidades (50%)': 0.0,
      'Deseos (30%)': 0.0,
      'Futuro (20%)': 0.0,
    };

    for (final tx in transactions) {
      if (tx.isExpense) {
        final meta = AppConfig.getCategoryMeta(tx.category);
        final grp = spentByGroup.containsKey(meta.group) ? meta.group : 'Deseos (30%)';
        spentByGroup[grp] = (spentByGroup[grp] ?? 0.0) + tx.amount;
      }
    }

    final Map<String, (double, Color)> groupRules = {
      'Necesidades (50%)': (0.50, const Color(0xFF60A5FA)),
      'Deseos (30%)': (0.30, const Color(0xFFC084FC)),
      'Futuro (20%)': (0.20, const Color(0xFF4ADE80)),
    };

    final totalSpent = spentByGroup.values.fold(0.0, (a, b) => a + b);
    final baseAmount = monthlyIncome > 0 ? monthlyIncome : max(totalSpent, 1.0);

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: colorScheme.surfaceContainerHighest.withOpacity(0.55),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: colorScheme.outlineVariant.withOpacity(0.4)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Expanded(
                child: Text(
                  'Presupuesto Regla 50 / 30 / 20',
                  style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              Icon(Icons.pie_chart_outline_rounded, size: 20, color: colorScheme.primary),
            ],
          ),
          const SizedBox(height: 4),
          Text(
            monthlyIncome > 0
                ? 'Límites sugeridos según tus ingresos del mes'
                : 'Registra tus ingresos del mes para ver tus topes sugeridos',
            style: TextStyle(fontSize: 11, color: colorScheme.onSurfaceVariant),
          ),
          const SizedBox(height: 12),
          ...groupRules.entries.map((entry) {
            final label = entry.key;
            final pct = entry.value.$1;
            final color = entry.value.$2;
            final spent = spentByGroup[label] ?? 0.0;
            final target = monthlyIncome > 0 ? monthlyIncome * pct : 0.0;
            final ratio = target > 0
                ? (spent / target).clamp(0.0, 1.0)
                : (spent / baseAmount).clamp(0.0, 1.0);
            final isOver = target > 0 && spent > target;

            final rightLabel = monthlyIncome > 0
                ? '${AppConfig.currencySymbol} ${fmt.format(spent)} / ${fmt.format(target)}'
                : '${AppConfig.currencySymbol} ${fmt.format(spent)}';

            return Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        label,
                        style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600),
                      ),
                      Flexible(
                        child: Text(
                          rightLabel,
                          style: TextStyle(
                            fontSize: 11,
                            fontWeight: isOver ? FontWeight.bold : FontWeight.normal,
                            color: isOver ? const Color(0xFFF87171) : colorScheme.onSurfaceVariant,
                          ),
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 5),
                  ClipRRect(
                    borderRadius: BorderRadius.circular(6),
                    child: LinearProgressIndicator(
                      value: ratio,
                      minHeight: 7,
                      backgroundColor: colorScheme.surface,
                      valueColor: AlwaysStoppedAnimation<Color>(
                        isOver ? const Color(0xFFF87171) : color,
                      ),
                    ),
                  ),
                ],
              ),
            );
          }),
        ],
      ),
    );
  }
}

class ExpensePieChartCard extends StatelessWidget {
  final List<TransactionModel> transactions;

  const ExpensePieChartCard({super.key, required this.transactions});

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    final fmt = NumberFormat('#,##0.00', 'en_US');
    final expenses = transactions.where((t) => t.isExpense).toList();
    final totalExpense = expenses.fold(0.0, (sum, t) => sum + t.amount);

    if (totalExpense <= 0) {
      return Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          color: colorScheme.surfaceContainerHighest.withOpacity(0.55),
          borderRadius: BorderRadius.circular(18),
          border: Border.all(color: colorScheme.outlineVariant.withOpacity(0.4)),
        ),
        child: Column(
          children: [
            Icon(Icons.donut_large_rounded, size: 38, color: colorScheme.onSurfaceVariant),
            const SizedBox(height: 8),
            const Text(
              'Distribución de Gastos por Categoría',
              style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 4),
            Text(
              'Sin gastos registrados en este mes',
              style: TextStyle(fontSize: 12, color: colorScheme.onSurfaceVariant),
            ),
          ],
        ),
      );
    }

    final Map<String, double> byCategory = {};
    for (final tx in expenses) {
      byCategory[tx.category] = (byCategory[tx.category] ?? 0.0) + tx.amount;
    }

    final sortedEntries = byCategory.entries.toList()
      ..sort((a, b) => b.value.compareTo(a.value));

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: colorScheme.surfaceContainerHighest.withOpacity(0.55),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: colorScheme.outlineVariant.withOpacity(0.4)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Distribución de Gastos por Categoría',
            style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 14),
          SizedBox(
            height: 170,
            child: PieChart(
              PieChartData(
                sectionsSpace: 2,
                centerSpaceRadius: 36,
                sections: sortedEntries.map((entry) {
                  final pct = (entry.value / totalExpense) * 100;
                  final meta = AppConfig.getCategoryMeta(entry.key);
                  return PieChartSectionData(
                    value: entry.value,
                    color: meta.color,
                    radius: 48,
                    title: pct >= 8 ? '${pct.round()}%' : '',
                    titleStyle: const TextStyle(
                      fontSize: 11,
                      fontWeight: FontWeight.bold,
                      color: Colors.white,
                    ),
                  );
                }).toList(),
              ),
            ),
          ),
          const SizedBox(height: 12),
          ...sortedEntries.map((entry) {
            final meta = AppConfig.getCategoryMeta(entry.key);
            return Padding(
              padding: const EdgeInsets.symmetric(vertical: 3),
              child: Row(
                children: [
                  Container(
                    width: 10,
                    height: 10,
                    decoration: BoxDecoration(color: meta.color, shape: BoxShape.circle),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      entry.key,
                      style: const TextStyle(fontSize: 12),
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  Text(
                    '${AppConfig.currencySymbol} ${fmt.format(entry.value)}',
                    style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600),
                  ),
                ],
              ),
            );
          }),
        ],
      ),
    );
  }
}

class CashflowBarChartCard extends StatelessWidget {
  final double monthlyIncome;
  final double monthlyExpense;

  const CashflowBarChartCard({
    super.key,
    required this.monthlyIncome,
    required this.monthlyExpense,
  });

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    final maxY = max(max(monthlyIncome, monthlyExpense), 100.0) * 1.25;

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: colorScheme.surfaceContainerHighest.withOpacity(0.55),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: colorScheme.outlineVariant.withOpacity(0.4)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Balance Comparativo (S/)',
            style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 14),
          SizedBox(
            height: 170,
            child: BarChart(
              BarChartData(
                maxY: maxY,
                gridData: FlGridData(
                  show: true,
                  drawVerticalLine: false,
                  horizontalInterval: maxY / 4,
                ),
                borderData: FlBorderData(show: false),
                titlesData: FlTitlesData(
                  topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                  rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                  leftTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                  bottomTitles: AxisTitles(
                    sideTitles: SideTitles(
                      showTitles: true,
                      getTitlesWidget: (value, meta) {
                        final label = value.toInt() == 0 ? 'Ingresos' : 'Gastos';
                        return Padding(
                          padding: const EdgeInsets.only(top: 6),
                          child: Text(label, style: const TextStyle(fontSize: 12)),
                        );
                      },
                    ),
                  ),
                ),
                barGroups: [
                  BarChartGroupData(
                    x: 0,
                    barRods: [
                      BarChartRodData(
                        toY: monthlyIncome,
                        color: const Color(0xFF2DD4BF),
                        width: 36,
                        borderRadius: const BorderRadius.vertical(top: Radius.circular(8)),
                      ),
                    ],
                  ),
                  BarChartGroupData(
                    x: 1,
                    barRods: [
                      BarChartRodData(
                        toY: monthlyExpense,
                        color: const Color(0xFFF87171),
                        width: 36,
                        borderRadius: const BorderRadius.vertical(top: Radius.circular(8)),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
