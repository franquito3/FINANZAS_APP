# Mis Finanzas (S/) — Flutter Nativo + Supabase Offline-First

Aplicación móvil de finanzas personales en Soles (`S/`) desarrollada en **Flutter nativo (Dart)** con arquitectura **Offline-First** y sincronización en la nube mediante **Supabase (`supabase_flutter`)**.

---

## Características Principales

- **Rendimiento Nativo a 60/120 FPS**: Compilada directamente a código nativo ARM para Android con Material 3.
- **Cero Desbordes de Teclado**: Formularios en `ModalBottomSheet` adaptativos (`viewInsets.bottom`) que se ajustan automáticamente al abrir el teclado numérico.
- **Calendario Financiero Interactivo (`table_calendar`)**:
  - Indicadores por día (punto verde para ingresos, punto rojo para gastos).
  - Filtro instantáneo por día, buscador en tiempo real, filtro por tipo y **Exportación a CSV**.
  - Selector de fecha rápido (*Hoy*, *Ayer* o cualquier fecha del calendario) al crear o editar movimientos.
- **Presupuesto Regla 50 / 30 / 20 y Gráficos (`fl_chart`)**:
  - Barras de progreso automáticas para *Necesidades (50%)*, *Deseos (30%)* y *Futuro (20%)*.
  - Gráfico circular interactivo por categoría y balance comparativo mensual.
- **Métodos de Pago / Cuentas**: Efectivo, Yape / Plin, Tarjeta Débito, Tarjeta Crédito y Transferencia.
- **Autenticación Dual en Supabase**:
  - **Correo y Contraseña** directo dentro de la app (Iniciar Sesión / Crear Cuenta).
  - **Google OAuth** con retorno automático por Deep Link (`misfinanzas://login-callback`).

---

## Cómo compilar el APK en GitHub Codespaces

Este repositorio incluye `.devcontainer/devcontainer.json` con **Flutter 3.24 + Android SDK** preinstalados:

1. Sube tus cambios a tu repositorio de GitHub (`git add . && git commit -m "Migración a Flutter nativo" && git push`).
2. En GitHub, haz clic en el botón verde **`<> Code`** $\rightarrow$ pestaña **Codespaces** $\rightarrow$ **Create codespace on main**.
3. Al abrirse la terminal de Codespaces, el entorno se configurará automáticamente. Para generar el APK ejecuta:
   ```bash
   flutter build apk --release
   ```
4. El archivo APK compilado quedará listo para descargar en:
   `build/app/outputs/flutter-apk/app-release.apk`

*(También se compila automáticamente en la pestaña **Actions** de GitHub en cada `git push` a `main`).*

---

## Configuración de URL para Google Login en Supabase

En tu panel de [Supabase](https://supabase.com/dashboard) ($\rightarrow$ **Authentication** $\rightarrow$ **URL Configuration** $\rightarrow$ **Redirect URLs**), asegúrate de tener agregadas:
- `misfinanzas://login-callback`
- `misfinanzas://**`
