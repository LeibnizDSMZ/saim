let
  nixpkgs_unstable = fetchTarball "https://github.com/NixOS/nixpkgs/tarball/nixos-unstable";
  pkgs_unstable = import nixpkgs_unstable {
    config = { };
    overlays = [ ];
  };
  pkgs = import <nixpkgs> { };
in
pkgs.mkShell {
  name = "config-shell";
  nativeBuildInputs = with pkgs; [
    git
    # python
    python313Full
    pkgs_unstable.virtualenv
    # python build requirements
    pkgs_unstable.pyenv
    gcc
    gnumake
    zlib
    libffi
    readline
    bzip2
    openssl
    ncurses
    sqlite
    xz
    stdenv.cc.cc
    tk
    tcl
    # format
    nixfmt-rfc-style
    ruff
  ];

  shellHook = ''
    export PATH=$HOME/.local/bin/:$PWD/.venv/bin/:$PATH
    export PYTHONPATH=$PWD/.venv/:$PYTHONPATH
    export RUFF=${pkgs.ruff}/bin/ruff

    export SOURCE_DATE_EPOCH=$(date +%s)
    export PYENV_ROOT="$HOME/.pyenv";

    # pyenv flags to be able to install Python
    export CPPFLAGS="-I${pkgs.zlib.dev}/include -I${pkgs.libffi.dev}/include -I${pkgs.readline.dev}/include -I${pkgs.bzip2.dev}/include -I${pkgs.openssl.dev}/include -I${pkgs.sqlite.dev}/include";
    export CFLAGS="-I${pkgs.openssl.dev}/include";
    export LDFLAGS="-L${pkgs.zlib.out}/lib -L${pkgs.libffi.out}/lib -L${pkgs.readline.out}/lib -L${pkgs.bzip2.out}/lib -L${pkgs.openssl.out}/lib -L${pkgs.sqlite.out}/lib -L${pkgs.stdenv.cc.cc.lib}/lib";

    export TCLTK_LIBS="-L${pkgs.tcl}/lib -L${pkgs.tk}/lib -l${pkgs.tcl.libPrefix} -l${pkgs.tk.libPrefix}"
    export TCLTK_CFLAGS="-I${pkgs.tcl}/include -I${pkgs.tk}/include"

    export LD_LIBRARY_PATH=${pkgs.stdenv.cc.cc.lib}/lib/:/run/opengl-driver/lib/

    export PYTHON_CONFIGURE_OPTS="--enable-shared --with-openssl=${pkgs.openssl.dev} --enable-loadable-sqlite-extensions";
    export PYENV_VIRTUALENV_DISABLE_PROMPT="1";
  '';
}
