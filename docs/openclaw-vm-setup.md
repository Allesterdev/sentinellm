# Configuración de OpenClaw en VM Ubuntu

## Ubicar archivo de configuración

OpenClaw normalmente guarda su configuración en uno de estos lugares:

```bash
# Buscar configuración de OpenClaw
~/.config/openclaw/config.json
~/.openclaw/config.json
~/openclaw/config.json
```

O puedes buscarla:
```bash
find ~ -name "*config*" -path "*openclaw*" 2>/dev/null
```

## Configurar OpenClaw para usar el proxy

1. **Editar la configuración** (ejemplo con nano):
```bash
nano ~/.config/openclaw/config.json
```

2. **Cambiar la URL del provider**:

**ANTES:**
```json
{
  "providers": {
    "openai": {
      "apiUrl": "https://api.openai.com",
      "apiKey": "sk-tu-clave-real"
    }
  }
}
```

**DESPUÉS:**
```json
{
  "providers": {
    "openai": {
      "apiUrl": "http://127.0.0.1:8080",
      "apiKey": "sk-tu-clave-real"
    }
  }
}
```

3. **Guardar y reiniciar OpenClaw**

## Verificar que funciona

1. **Iniciar el proxy en una terminal:**
```bash
cd ~/sentinellm  # o donde esté instalado
source venv/bin/activate
python sentinellm.py proxy
```

2. **En otra terminal, ejecutar OpenClaw:**
```bash
openclaw
```

3. **Probar con un mensaje que contenga un secreto:**
```
Hola, mi API key es sk-proj-45lP0XfR89dVtZ2kL1mV3nQo6jS7bA9cE0hOcSI34wK
```

**Resultado esperado:** El proxy debe mostrar un log bloqueando el mensaje y OpenClaw debe recibir un error 403.

## Troubleshooting

### Si sigue sin funcionar:

1. **Verificar que el proxy está escuchando:**
```bash
curl http://127.0.0.1:8080/health
# Debe responder: {"status":"healthy","service":"sentinellm-proxy"}
```

2. **Ver logs del proxy:**
   - Debe aparecer cada request que llega
   - Si no aparece nada = OpenClaw no está usando el proxy

3. **Revisar variables de entorno:**
```bash
env | grep -i openai
# Asegurarse que no hay OPENAI_API_URL sobreescribiendo la config
```
