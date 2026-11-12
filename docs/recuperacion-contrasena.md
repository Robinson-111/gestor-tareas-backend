# Recuperación de contraseña ("¿Olvidaste tu contraseña?")

Flujo de auto-servicio: el usuario solicita un **enlace por correo** y define una
nueva contraseña. No hay librerías nuevas; se usa el token generator de Django
(`django.contrib.auth.tokens.default_token_generator`).

## 1. Flujo

```
Frontend                          Backend                        Correo
   |                                |                              |
   |-- clic "¿Olvidaste tu...?" --> |                              |
   |   /forgot-password             |                              |
   |                                |                              |
   |-- POST /auth/password-reset -->|                              |
   |   { "email": "..." }           |-- usuario activo? ----------|
   |                                |-- genera uidb64 + token      |
   |<-- 200 genérico (siempre) -----|-- envía correo con enlace -->|
   |                                |                              |
   |   usuario abre el enlace       |                              |
   |   /reset-password?uidb64&token |                              |
   |                                |                              |
   |-- POST /auth/password-reset/confirm/                         |
   |   { uidb64, token, new_password, confirm_password }          |
   |                                |-- valida token + validators  |
   |                                |-- set_password + blacklist   |
   |<-- 200 "Contraseña actualizada exitosamente."                |
```

## 2. Endpoints

### `POST /api/v1/auth/password-reset/`

**Público.** Limitado a **5 peticiones por minuto por IP** (`PASSWORD_RESET_THROTTLE_RATE`).

```json
{ "email": "ana@example.com" }
```

- **Siempre responde 200** con un mensaje genérico, exista o no la cuenta.
  Evita enumerar correos registrados.
- Solo envía correo si existe un usuario **activo** con ese correo (sin distinguir
  mayúsculas/minúsculas).

**200 OK**

```json
{
  "message": "Si el correo está registrado, recibirás un enlace para restablecer tu contraseña."
}
```

### `POST /api/v1/auth/password-reset/confirm/`

**Público.** Mismo throttling que la solicitud.

```json
{
  "uidb64": "MTM",
  "token": "dhwa9v-ab18680...",
  "new_password": "Xk9#mQ2vLp7z",
  "confirm_password": "Xk9#mQ2vLp7z"
}
```

Reglas:

- `uidb64` + `token` provienen del enlace del correo.
- Se aplican los `AUTH_PASSWORD_VALIDATORS` a la nueva contraseña.
- `confirm_password` debe coincidir.

**200 OK**

```json
{ "message": "Contraseña actualizada exitosamente." }
```

**400 Bad Request** — enlace inválido/expirado o validación fallida:

```json
{ "message": "El enlace es inválido o ha expirado." }
```

```json
{
  "message": "Revisa los campos del formulario.",
  "errors": {
    "new_password": ["Esta contraseña es demasiado corta. Debe contener al menos 8 caracteres."]
  }
}
```

```json
{
  "message": "Revisa los campos del formulario.",
  "errors": {
    "confirm_password": ["Las contraseñas no coinciden."]
  }
}
```

## 3. Seguridad

| Medida | Detalle |
|---|---|
| Token de un solo uso | `default_token_generator` invalida el token al cambiar la contraseña. Reusar el enlace da 400. |
| Expiración | 1 hora por defecto (`PASSWORD_RESET_TIMEOUT=3600`, en segundos). |
| Anti-enumeración | La solicitud responde siempre lo mismo y no envía correo a usuarios inexistentes o inactivos. |
| Throttling | `password_reset` scope: 5/min por IP. |
| Cierre de sesiones | Al confirmar, **todos los refresh tokens** del usuario quedan en blacklist (`OutstandingToken` → `BlacklistedToken`). Los access tokens vigentes siguen funcionando hasta 15 minutos. |
| Validadores | `validate_password(password, user=user)` aplica `UserAttributeSimilarityValidator`, `MinimumLengthValidator`, `CommonPasswordValidator` y `NumericPasswordValidator`. |

## 4. Configuración (`.env`)

```env
FRONTEND_URL=http://localhost:5173          # construye el enlace del correo
PASSWORD_RESET_TIMEOUT=3600                 # vida útil del token (segundos)
PASSWORD_RESET_THROTTLE_RATE=5/min

DEFAULT_FROM_EMAIL=TaskFlow <no-reply@taskflow.local>
MAIL_HOST=                                  # SMTP real; vacío => consola
MAIL_PORT=587
MAIL_USERNAME=
MAIL_PASSWORD=
MAIL_USE_TLS=True
MAIL_TIMEOUT=10
```

- **Desarrollo sin SMTP**: `MAIL_HOST`/`MAIL_USERNAME` vacíos → el correo se
  imprime en la consola del backend y el enlace se puede copiar de ahí.
- **SMTP real**: llenar `MAIL_HOST`, `MAIL_USERNAME`, `MAIL_PASSWORD` (y ajustar
  `DEFAULT_FROM_EMAIL` a un remitente verificado). Se configura en
  `MAILERS['default']` (API nueva de correo de Django 6.1).

## 5. Frontend

- `LoginPage`: el botón "¿Olvidaste tu contraseña?" lleva a `/forgot-password`.
- `ForgotPasswordPage`: pide el correo; tras enviar muestra estado de éxito
  ("Revisa tu correo") y permite reintentar con otro correo.
- `ResetPasswordPage`: lee `uidb64` y `token` del query string, pide nueva
  contraseña + confirmación. Si faltan parámetros muestra "Enlace no válido".
  Al confirmar redirige a `/login` con toast.

## 6. Pruebas

```bash
python manage.py test auth.tests.PasswordResetTests
```

14 pruebas cubren: envío a usuario existente, respuesta genérica y silenciosa,
usuarios inactivos, validación de campos, cambio de contraseña, login con la
nueva clave, blacklist de refresh tokens previos, token inválido, uid inválido,
contraseñas que no coinciden, contraseña débil y token de un solo uso.
