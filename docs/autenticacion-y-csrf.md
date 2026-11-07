# Seguridad de autenticación, CORS y CSRF

Documento de decisión para el paso a producción del Gestor de Tareas Colaborativo.
Aplica a la sección 18 de los requerimientos (JWT, cookies HttpOnly, sesiones simultáneas).

## 1. Estado actual

- Autenticación por **JWT en el header** `Authorization: Bearer <access>`.
- `access` (15 min) y `refresh` (7 días) se devuelven en el **body JSON** de `/api/v1/auth/login/`.
- `SessionAuthentication` **no** está habilitada: DRF no valida CSRF.
- Como consecuencia, **hoy no hay exposición a CSRF**, porque el navegador no envía
  credenciales automáticamente al API.
- `DEFAULT_PERMISSION_CLASSES = IsAuthenticated`: todo endpoint es privado salvo
  `/api/v1/auth/register/`, `/api/v1/auth/login/`, `/api/v1/auth/logout/` y `/api/v1/auth/refresh/`.
- CORS restringido a los orígenes declarados en `CORS_ALLOWED_ORIGINS`.
- Endurecimiento de producción (HTTPS, HSTS, cookies seguras) se activa con `DEBUG=False`.

## 2. Objetivo según los requerimientos

| Requisito | Definición |
|---|---|
| RN-35 / 18.6 | Tokens gestionados con cookies **HttpOnly** |
| RN-36 / 18.7 | Logout elimina las cookies de la sesión |
| RN-37 | Sin revocación individual de refresh tokens en el MVP |
| RN-38/39 | Sesiones simultáneas independientes |
| RN-32/33 | Access 15 min, refresh 7 días |

## 3. Diseño propuesto (pendiente de implementar)

### 3.1 Cookies

- `access_token`: `HttpOnly`, `Secure` (prod), `SameSite=Lax`, `Path=/`.
- `refresh_token`: `HttpOnly`, `Secure` (prod), `SameSite=Strict`, `Path=/api/v1/auth/refresh/`.
- `logout` debe limpiar ambas cookies con `delete_cookie` (mismo `path` y `domain`).
- No usar `Domain` amplio: dejar la cookie limitada al host del API.

### 3.2 CSRF

Al pasar los tokens a cookies, el navegador los envía automáticamente y **CSRF pasa a ser
un riesgo real**. Se propone doble protección:

1. `SameSite=Lax` en `access_token` y `Strict` en `refresh_token`.
2. Token CSRF de doble envío:
   - El API expone `GET /api/v1/auth/csrf/` que devuelve un token en una cookie **no HttpOnly**
     (`csrftoken`) o en el body.
   - El front lo envía en el header `X-CSRFToken` en cada `POST/PATCH/DELETE`.
   - El API valida con `django.middleware.csrf` (`@csrf_protect` o `SessionAuthentication`
     si se habilita).

Configuración necesaria (`config/settings.py` ya preparada):

```python
CSRF_TRUSTED_ORIGINS = env.list('CSRF_TRUSTED_ORIGINS', default=[])
CORS_ALLOW_CREDENTIALS = env.bool('CORS_ALLOW_CREDENTIALS', default=False)
```

- `CORS_ALLOW_CREDENTIALS=True` **solo** con orígenes explícitos (nunca `*`).
- `CSRF_COOKIE_SECURE=True` y `CSRF_COOKIE_SAMESITE='Lax'` en producción.

### 3.3 Flujo

1. `POST /api/v1/auth/login/` valida credenciales y responde `Set-Cookie` con ambos tokens.
2. `POST /api/v1/auth/refresh/` lee `refresh_token` de la cookie, rota el token (ya configurado
   `ROTATE_REFRESH_TOKENS`) y emite nuevas cookies.
3. `POST /api/v1/auth/logout/` lee la cookie de refresh, la blacklistea y elimina las cookies.
4. El front **no** guarda tokens en `localStorage` ni los lee por JS (HttpOnly).

### 3.4 Notas

- Con cookies, `CORS_ALLOW_CREDENTIALS=True` y `CORS_ALLOWED_ORIGINS` explícito son
  obligatorios.
- El throttle de login usa la caché configurada; con múltiples workers/procesos
  (`LocMemCache`) el límite es por proceso. Para producción usar Redis/Memcached.
- Rotar `SECRET_KEY` invalida todos los tokens emitidos: coordinar con el despliegue.
- Si se mantiene el esquema actual de header `Authorization`, este documento no es
  necesario, pero se incumple RN-35/18.6.

## 4. Checklist antes de producción

- [x] `SECRET_KEY` fuera del repositorio (variable de entorno).
- [x] `DEBUG` desde entorno, apagado por defecto.
- [x] `ALLOWED_HOSTS` configurable.
- [x] CORS con orígenes explícitos.
- [x] `DEFAULT_PERMISSION_CLASSES = IsAuthenticated`.
- [x] Throttling en login.
- [x] Validadores de contraseña aplicados en registro.
- [ ] Migrar tokens a cookies HttpOnly.
- [ ] Implementar validación CSRF de doble envío.
- [ ] Cache compartida para throttling (Redis).
- [ ] Forzar HTTPS y revisar `SECURE_PROXY_SSL_HEADER` en el proxy.
