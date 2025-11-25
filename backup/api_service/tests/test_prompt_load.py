import os
from pathlib import Path

print('=' * 60)
print('SIMULACIÓN DE CARGA DE PROMPT (como analysis.py)')
print('=' * 60)
print()

# 1. Obtener nombre del archivo
prompt_file_name = os.getenv('PROMPT_FILE', 'prompt.txt')
print(f'1. Archivo a cargar: {prompt_file_name}')
print()

# 2. Construir path
api_service_dir = Path.cwd()
prompt_file_path = api_service_dir / prompt_file_name

print(f'2. Path completo: {prompt_file_path}')
print(f'3. Existe: {prompt_file_path.exists()}')
print()

# 3. Cargar contenido
if prompt_file_path.exists():
    content = prompt_file_path.read_text(encoding='utf-8')
    print(f'4. ✅ Cargado exitosamente: {len(content)} caracteres')
    print()
    print('5. Preview (primeros 300 caracteres):')
    print('-' * 60)
    print(content[:300])
    print('...')
    print('-' * 60)
    print()

    # 4. Verificar contenido
    checks = {
        'executive_summary': 'executive_summary' in content,
        'top_performers': 'top_performers' in content,
        'strategic_recommendations': 'strategic_recommendations' in content,
        'visual_composition': 'visual_composition' in content,
        'PASO 1': 'PASO 1' in content,
        'PASO 7': 'PASO 7' in content,
    }

    print('6. Verificaciones de estructura:')
    for key, value in checks.items():
        status = '✅' if value else '❌'
        print(f'   {status} {key}: {value}')
    print()

    if all(checks.values()):
        print('=' * 60)
        print('✅ PROMPT COMPLETAMENTE LISTO PARA USAR CON IA')
        print('=' * 60)
        print()
        print('El prompt será enviado a OpenAI con:')
        print(f'  • {len(content)} caracteres de instrucciones')
        print('  • Estructura JSON completa definida')
        print('  • 7 pasos de análisis detallados')
        print('  • Metadatos CSV incluidos en el mensaje')
        print('  • Imágenes adjuntas como base64')
    else:
        print('⚠️ ADVERTENCIA: Faltan elementos en el prompt')
else:
    print(f'❌ ERROR: Archivo {prompt_file_path} no encontrado')
