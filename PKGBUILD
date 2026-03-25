# Maintainer: Ashutosh Tiwari <contact@ashutoshtiwari.dev>
pkgname=qwarp
pkgver=0.3.0_alpha
pkgrel=1
pkgdesc="A lightweight, Wayland-native Qt6 wrapper for cloudflare-warp-bin"
arch=('any')
url="https://github.com/iashutoshtiwari/qwarp"
license=('MIT')
depends=('python' 'python-pyqt6' 'cloudflare-warp-bin')
makedepends=('python-build' 'python-installer' 'python-wheel' 'python-setuptools')

# We use bash substitution ${pkgver/_/-} to convert "0.2.0_alpha" back to "0.2.0-alpha"
# so pacman respects the underscore rule, but GitHub can still find your tag.
source=("$pkgname-$pkgver.tar.gz::https://github.com/iashutoshtiwari/qwarp/archive/refs/tags/v${pkgver/_/-}.tar.gz")
sha256sums=('e32def3ee489f2a2d39b3feb08cd3277dddaf0d09f96f7ae9e87a6aa4d2497a0')

build() {
  # GitHub extracts tarballs into a folder named <repo>-<tag>
  cd "$pkgname-${pkgver/_/-}"
  python -m build --wheel --no-isolation
}

package() {
  cd "$pkgname-${pkgver/_/-}"

  local _wheels=(dist/*.whl)

  if [ ! -f "${_wheels[0]}" ]; then
      echo "Error: No wheel found in dist/"
      exit 1
  fi

  python -m installer --destdir="$pkgdir" "${_wheels[0]}"
  install -Dm644 qwarp.desktop "$pkgdir/usr/share/applications/qwarp.desktop"
  install -Dm644 LICENSE "$pkgdir/usr/share/licenses/$pkgname/LICENSE"
}
