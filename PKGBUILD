# Maintainer: Ashutosh
pkgname=qwarp
pkgver=0.1.0
pkgrel=1
pkgdesc="A lightweight, Wayland-native Qt6 wrapper for cloudflare-warp-bin"
arch=('any')
license=('MIT')
depends=('python' 'python-pyqt6' 'cloudflare-warp-bin')
makedepends=('python-build' 'python-installer' 'python-wheel' 'python-setuptools')
source=()

build() {
  # Force makepkg to run exactly where the PKGBUILD is located
  cd "$startdir"
  python -m build --wheel --no-isolation
}

package() {
  # Force fakeroot to look in your actual project directory
  cd "$startdir"
  
  local _wheels=(dist/*.whl)
  
  if [ ! -f "${_wheels[0]}" ]; then
      echo "Error: No wheel found in dist/"
      exit 1
  fi

  python -m installer --destdir="$pkgdir" "${_wheels[0]}"
  install -Dm644 qwarp.desktop "$pkgdir/usr/share/applications/qwarp.desktop"
  install -Dm644 LICENSE "$pkgdir/usr/share/licenses/$pkgname/LICENSE"
}