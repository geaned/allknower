### For MacOS users

In case of receiving an error related to `pycurl` being compiled without an SSL backend, input the following commands

```bash
brew install openssl    # if not installed
export PYCURL_SSL_LIBRARY=openssl
export PATH="/opt/homebrew/opt/openssl@3/bin:$PATH"
export LDFLAGS="-L/opt/homebrew/opt/openssl@3/lib"
export CPPFLAGS="-I/opt/homebrew/opt/openssl@3/include"
export PKG_CONFIG_PATH="/opt/homebrew/opt/openssl@3/lib/pkgconfig"
pip uninstall pycurl
pip install --no-cache-dir --compile --ignore-installed pycurl
```
