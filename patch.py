#!/usr/bin/env python3
"""
patch.py  —  SEARCH/REPLACE tabanlı dosya düzenleme aracı
----------------------------------------------------------
Kullanım:
    python patch.py <hedef_dosya> <patch_dosyası>
    python patch.py <hedef_dosya> -                     # stdin'den oku
    python patch.py <hedef_dosya> --goster [N]          # dosyayı göster (N civarı)
    python patch.py <hedef_dosya> --geri                # .bak yedeğine dön

Patch dosyası formatı (birden fazla blok --- ile ayrılır):
    SEARCH:
    eski metin
    tam olarak böyle
    REPLACE:
    yeni metin
    işte böyle
    ---
    SEARCH:
    başka bir şey
    REPLACE:
    onun yerine bu

Git desteği (opsiyonel, klasörde .git varsa otomatik commit+push):
    python patch.py scrape.py degisiklik.patch
    → git add scrape.py && git commit -m "patch: scrape.py" && git push

Örnekler:
    echo 'SEARCH:
    gebe":7
    REPLACE:
    gebe":8' | python patch.py scrape.py -
"""

import sys
import shutil
import subprocess
from pathlib import Path


# ── Yedek ─────────────────────────────────────────────────────────────────────

def backup(path: Path):
    bak = Path(str(path) + ".bak")
    shutil.copy2(path, bak)


def restore(path: Path):
    bak = Path(str(path) + ".bak")
    if not bak.exists():
        die(f"Yedek bulunamadı: {bak}")
    shutil.copy2(bak, path)
    ok(f"Geri alındı: {path}  ←  {bak}")


# ── Çıktı ─────────────────────────────────────────────────────────────────────

def ok(msg):    print(f"✅  {msg}")
def warn(msg):  print(f"⚠️   {msg}")
def die(msg):   print(f"❌  {msg}"); sys.exit(1)


# ── SEARCH/REPLACE motor ──────────────────────────────────────────────────────

def apply_patch(target: Path, raw: str) -> bool:
    """
    raw içindeki tüm SEARCH/REPLACE bloklarını uygula.
    Herhangi biri başarısız olursa False dön, dosyayı değiştirme.
    """
    blocks = [b for b in raw.split("---\n") if "SEARCH:" in b and "REPLACE:" in b]

    if not blocks:
        die("Geçerli SEARCH/REPLACE bloğu bulunamadı.")

    content = target.read_text(encoding="utf-8")
    working = content  # önce kopyada dene

    for i, block in enumerate(blocks, 1):
        after_search  = block.split("SEARCH:", 1)[1]
        parts         = after_search.split("REPLACE:", 1)
        search_text   = parts[0].lstrip("\n").rstrip("\n")
        replace_text  = parts[1].lstrip("\n").rstrip("\n")

        if search_text not in working:
            warn(f"Blok {i}: bulunamadı →\n    {search_text[:80]!r}")
            return False

        working = working.replace(search_text, replace_text, 1)
        ok(f"Blok {i}: uygulandı  [{search_text[:50].strip()!r} → ...]")

    # Tümü başarılı — yedek al, yaz
    backup(target)
    target.write_text(working, encoding="utf-8")
    return True


# ── Git ───────────────────────────────────────────────────────────────────────

def git_commit_push(target: Path):
    repo = target.parent
    # .git bul (üst klasörlere de bak)
    check = repo
    for _ in range(5):
        if (check / ".git").exists():
            break
        check = check.parent
    else:
        return  # git yok, sessizce geç

    msg = input("Commit mesajı (boş bırakırsan otomatik): ").strip()
    if not msg:
        msg = f"patch: {target.name}"
    subprocess.run(["git", "add", str(target)], cwd=check)
    subprocess.run(["git", "commit", "-m", msg], cwd=check)
    push = subprocess.run(["git", "push"], cwd=check, capture_output=True, text=True)
    if push.returncode == 0:
        ok("Git: commit + push tamam")
    else:
        warn(f"Git push hatası:\n{push.stderr.strip()}")


# ── Göster ────────────────────────────────────────────────────────────────────

def show(path: Path, around: int = None):
    lines = path.read_text(encoding="utf-8").splitlines()
    if around:
        start = max(0, around - 6)
        end   = min(len(lines), around + 6)
        for i, line in enumerate(lines[start:end], start=start + 1):
            marker = ">>>" if i == around else "   "
            print(f"{marker} {i:4d}  {line}")
    else:
        for i, line in enumerate(lines, 1):
            print(f"  {i:4d}  {line}")


# ── Ana akış ──────────────────────────────────────────────────────────────────

def main():
    args = sys.argv[1:]

    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0)

    target = Path(args[0])

    # Sadece dosya adı verilmişse → göster
    if len(args) == 1:
        if not target.exists():
            die(f"Dosya bulunamadı: {target}")
        show(target)
        return

    komut = args[1]

    # --geri
    if komut == "--geri":
        if not target.exists() and not Path(str(target) + ".bak").exists():
            die(f"Dosya bulunamadı: {target}")
        restore(target)
        return

    # --goster [N]
    if komut == "--goster":
        if not target.exists():
            die(f"Dosya bulunamadı: {target}")
        n = int(args[2]) if len(args) > 2 else None
        show(target, n)
        return

    # patch modu: python patch.py hedef patch_dosyası | -
    if not target.exists():
        die(f"Hedef dosya bulunamadı: {target}")

    if komut == "-":
        raw = sys.stdin.read()
    else:
        patch_file = Path(komut)
        if not patch_file.exists():
            die(f"Patch dosyası bulunamadı: {patch_file}")
        raw = patch_file.read_text(encoding="utf-8")

    success = apply_patch(target, raw)
    if not success:
        die("Patch uygulanamadı. Dosya değiştirilmedi.")

    git_commit_push(target)


if __name__ == "__main__":
    main()
