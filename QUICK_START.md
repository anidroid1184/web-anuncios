# 🚀 Inicio Rápido

## Iniciar el Proyecto

### Método Recomendado (Más Limpio)

```bash
python start.py
```

Esto inicia ambos servidores automáticamente:
- ✅ API en puerto **8001**
- ✅ Frontend en puerto **3001**
- ✅ Output organizado con prefijos `[API]` y `[FRONTEND]`
- ✅ Detención con CTRL+C cierra ambos servidores

### URLs Importantes

Una vez iniciado:

- 🌐 **Frontend**: http://localhost:3001/
- 📡 **API**: http://localhost:8001/
- 📚 **API Docs**: http://localhost:8001/docs

### Detener Servidores

Presiona `CTRL+C` en la terminal donde ejecutaste `start.py`

---

## Alternativas

### Solo API

```bash
python start.py --api-only
# o
python scripts/start-api.py
```

### Solo Frontend

```bash
python start.py --frontend-only
# o
python scripts/start-frontend.py
```

---

## Solución de Problemas

### Puerto ya en uso

Si ves un mensaje de que el puerto está en uso:

**Windows:**
```powershell
# Ver qué proceso usa el puerto 8001
netstat -ano | findstr :8001
# Matar el proceso (reemplaza PID con el número que veas)
taskkill /PID <PID> /F

# Para puerto 3001
netstat -ano | findstr :3001
taskkill /PID <PID> /F
```

**Linux/Mac:**
```bash
# Ver qué proceso usa el puerto 8001
lsof -i :8001
# Matar el proceso
kill -9 <PID>

# Para puerto 3001
lsof -i :3001
kill -9 <PID>
```

### Los colores no se muestran

El script `start.py` usa colores ANSI. Si no se muestran correctamente en tu terminal:
- **Windows**: Usa Windows Terminal o PowerShell (no CMD antiguo)
- **Linux/Mac**: Deberían funcionar por defecto

Si aún no funcionan, puedes usar los scripts individuales que no usan colores.




