# Maintainer: Ashutosh Tiwari <contact@ashutoshtiwari.dev>
pkgname=qwarp
pkgver=0.4.0_alpha
pkgrel=1
pkgdesc="A lightweight, Wayland-native Qt6 wrapper for cloudflare-warp-bin"
arch=('any')
url="https://github.com/iashutoshtiwari/qwarp"
license=('MIT')
depends=('python' 'python-pyqt6' 'cloudflare-warp-bin')
makedepends=('python-build' 'python-installer' 'python-wheel' 'python-setuptools')

# We use bash substitution ${pkgver/_/-} to convert "0.3.0_alpha" back to "0.3.0-alpha"
# so pacman respects the underscore rule, but GitHub can still find your tag.
source=("$pkgname-$pkgver.tar.gz::https://github.com/iashutoshtiwari/qwarp/archive/refs/tags/v${pkgver/_/-}.tar.gz")
sha256sums=('SKIP') # Temporarily skipping hash check for local builds.

build() {
  # For local testing, build from the startdir so uncommitted changes are included
  cd "$startdir"
  python -m build --wheel --no-isolation
}

package() {
  # Use local startdir to package uncommitted assets and wheels correctly
  cd "$startdir"

  local _wheels=(dist/*.whl)

  if [ ! -f "${_wheels[0]}" ]; then
      echo "Error: No wheel found in dist/"
      exit 1
  fi

  # Install the Python package
  python -m installer --destdir="$pkgdir" "${_wheels[0]}"

  # Install the desktop entry
  install -Dm644 qwarp.desktop "$pkgdir/usr/share/applications/qwarp.desktop"

  # THE FIX: Explicitly point to the source directory for the icon
  install -Dm644 "src/qwarp/assets/app-icon.svg" "$pkgdir/usr/share/icons/hicolor/scalable/apps/qwarp.svg"

  # Install the license
  install -Dm644 LICENSE "$pkgdir/usr/share/licenses/$pkgname/LICENSE"
}
