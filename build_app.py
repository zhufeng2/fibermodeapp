"""打包脚本 - macOS (.app) 和 Windows (.exe) 通用"""
import PyInstaller.__main__
import os
import sys
import shutil

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
DIST_DIR = os.path.join(PROJECT_DIR, "dist")
BUILD_DIR = os.path.join(PROJECT_DIR, "build")

for d in [DIST_DIR, BUILD_DIR]:
    if os.path.exists(d):
        shutil.rmtree(d)
for f in ["FiberMode.spec"]:
    if os.path.exists(os.path.join(PROJECT_DIR, f)):
        os.remove(os.path.join(PROJECT_DIR, f))

args = [
    "main.py",
    "--onedir" if sys.platform == "darwin" else "--onefile",
    "--windowed",
    "--name=FiberMode",
    "--distpath=" + DIST_DIR,
    "--workpath=" + BUILD_DIR,
    "--specpath=" + PROJECT_DIR,
    "--noupx",
    # 只排除完全独立、确认不被 scipy 内部依赖的模块
    "--exclude-module=matplotlib",
    "--exclude-module=pandas",
    "--exclude-module=sklearn",
    "--exclude-module=tensorflow",
    "--exclude-module=torch",
    "--exclude-module=IPython",
    "--exclude-module=jupyter",
    "--exclude-module=notebook",
    "--exclude-module=pytest",
    # 确保必要模块被打包
    "--hidden-import=PIL._tkinter_finder",
    "--hidden-import=scipy.special._ufuncs_cxx",
    "--hidden-import=scipy.linalg.cython_blas",
    "--hidden-import=scipy.linalg.cython_lapack",
]

print(f"Platform: {sys.platform}")
print("Building FiberMode...")
PyInstaller.__main__.run(args)

if sys.platform == "darwin":
    out = os.path.join(DIST_DIR, "FiberMode.app")
    if os.path.exists(out):
        import subprocess
        subprocess.run(["xattr", "-cr", out])
        subprocess.run(["/usr/bin/codesign", "-s", "-", "--force", "--deep", out])
        size = sum(
            os.path.getsize(os.path.join(dp, f))
            for dp, _, files in os.walk(out)
            for f in files
        ) / 1024 / 1024
        print(f"\nBuild complete: {out} ({size:.0f} MB)")
else:
    out = os.path.join(DIST_DIR, "FiberMode.exe")
    if os.path.exists(out):
        size_mb = os.path.getsize(out) / 1024 / 1024
        print(f"\nBuild complete: {out} ({size_mb:.0f} MB)")
