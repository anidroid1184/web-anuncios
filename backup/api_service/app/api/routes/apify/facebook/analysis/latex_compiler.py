"""
LaTeX Compiler Module
Compila archivos .tex a PDF usando pdflatex
"""
import subprocess
import shutil
from pathlib import Path
from typing import Dict, Any


def compile_latex_to_pdf(
    tex_path: Path,
    output_dir: Path
) -> Dict[str, Any]:
    """
    Compila un archivo LaTeX a PDF usando pdflatex

    Args:
        tex_path: Ruta al archivo .tex
        output_dir: Directorio donde guardar el PDF

    Returns:
        Dict con success, pdf_filename, y error (si hay)
    """
    # Verificar si pdflatex está disponible
    if not shutil.which('pdflatex'):
        return {
            'success': False,
            'error': 'pdflatex not found. Install TeX Live or MiKTeX',
            'pdf_filename': None
        }

    try:
        # Ejecutar pdflatex
        # -interaction=nonstopmode: no detiene en errores
        # -output-directory: donde guardar archivos generados
        result = subprocess.run(
            [
                'pdflatex',
                '-interaction=nonstopmode',
                f'-output-directory={output_dir}',
                str(tex_path)
            ],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=output_dir
        )

        # El PDF debería tener el mismo nombre que el .tex
        pdf_filename = tex_path.stem + '.pdf'
        pdf_path = output_dir / pdf_filename

        if pdf_path.exists():
            # Limpiar archivos auxiliares (.aux, .log, etc)
            for ext in ['.aux', '.log', '.out']:
                aux_file = output_dir / (tex_path.stem + ext)
                if aux_file.exists():
                    try:
                        aux_file.unlink()
                    except Exception:
                        pass

            return {
                'success': True,
                'pdf_filename': pdf_filename,
                'error': None
            }
        else:
            # PDF no generado, extraer error del log
            error_msg = 'PDF compilation failed'
            if result.returncode != 0:
                error_msg += f': {result.stderr[:500]}'

            return {
                'success': False,
                'error': error_msg,
                'pdf_filename': None
            }

    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'error': 'LaTeX compilation timeout (>60s)',
            'pdf_filename': None
        }
    except Exception as e:
        return {
            'success': False,
            'error': f'Compilation error: {str(e)}',
            'pdf_filename': None
        }
