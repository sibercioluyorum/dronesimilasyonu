"""
Pytest için yapılandırma ve fixture'lar
"""

def pytest_configure(config):
    """
    Pytest yapılandırması
    src dizininin import edilebilmesi için gerekli ayarları yapar
    """
    import sys
    from pathlib import Path
    
    # src dizininin bir üst klasörünü Python path'ine ekle
    root_dir = Path(__file__).parent.parent.parent
    sys.path.append(str(root_dir))