"""perl — Practical Extraction and Report Language.

Like nixpkgs/pkgs/development/interpreters/perl/interpreter.nix.
Uses stage1 stdenv. Multi-output: out, man, devdoc.

Bootstrap variant: enableThreading=false, enableCrypt=false (from default.nix
override in pkgs/stdenv/linux/default.nix line 354-357).

Perl's build uses its own Configure script (not autoconf), so configureScript
is overridden to "${shell} ./Configure". The -de flag tells Configure to use
all defaults without prompting.

The preConfigure phase:
  1. Writes config.over for reproducible build metadata (osvers, myuname, etc.)
  2. Points Compress::Raw::Zlib at our zlib instead of the bundled one
  3. Strips pthread from Configure (bootstrap doesn't have static libpthread)

The postInstall phase removes references to glibc, gcc-wrapper, and
bootstrap-tools from Config_heavy.pl to avoid unwanted runtime closures.
"""

from pix.store_path import placeholder
from pixpkgs.drv import Package
from pixpkgs.mk_derivation import mk_derivation
from pixpkgs.vendor import (
    PERL_CVE_2024_56406,
    PERL_CVE_2025_40909,
    PERL_FIX_C_LOCALE,
    PERL_NO_SYS_DIRS,
    PERL_SETUP_HOOK,
)


def make_perl(
    bootstrap_tools: Package,
    stdenv: Package,
    src: Package,
    zlib: Package,
    glibc_bootstrap_files: Package,
    gcc_wrapper: Package,
) -> Package:
    bt = str(bootstrap_tools)
    glibc = str(glibc_bootstrap_files)
    gcc_w = str(gcc_wrapper)
    # zlib is multi-output: need both dev (headers) and out (libs)
    zlib_dev = zlib.outputs["dev"]
    zlib_out = zlib.outputs["out"]

    # Perl's configureFlags use the output placeholder for -Dprefix and -Dman*dir.
    # In Nix, `placeholder "out"` produces a 52-char nix-base32 hash string
    # that gets substituted at build time.  mk_derivation handles this via
    # the drv() pipeline: output paths are blank at env-construction time,
    # then filled in after hashDerivationModulo.  We use the same placeholder
    # pattern that drv() will fill in.
    #
    # The preConfigure script references zlib paths and the postInstall
    # references glibc, gcc-wrapper, and bootstrap-tools paths.

    patches = " ".join([
        PERL_CVE_2024_56406,
        PERL_CVE_2025_40909,
        PERL_NO_SYS_DIRS,
        PERL_FIX_C_LOCALE,
    ])

    # Perl's Configure is not autoconf — no --prefix, uses -D flags instead.
    # -de = use defaults, no prompting.
    # -Dprefix is set to placeholder "out" by the drv pipeline.
    # -Dcc=cc because stdenv.cc.targetPrefix is "" for native builds.
    # -Duseshrplib builds a shared libperl.so.
    # -Dlocincpth/-Dloclibpth point at glibc headers/libs.
    # -A clear:d_crypt_r because enableCrypt=false.

    post_install = (
        '# Remove dependency between "out" and "man" outputs.\n'
        'rm "$out"/lib/perl5/*/*/.packlist\n'
        "\n"
        "# Remove dependencies on glibc and gcc\n"
        "sed \"/ *libpth =>/c    libpth => ' ',\" \\\n"
        '  -i "$out"/lib/perl5/*/*/Config.pm\n'
        "# TODO: removing those paths would be cleaner than overwriting with nonsense.\n"
        'substituteInPlace "$out"/lib/perl5/*/*/Config_heavy.pl \\\n'
        f'  --replace "{glibc}" /no-such-path \\\n'
        f'  --replace "{gcc_w}" /no-such-path \\\n'
        f'  --replace "{bt}" /no-such-path \\\n'
        '  --replace "/no-such-path" /no-such-path \\\n'
        '  --replace "$man" /no-such-path\n'
    )

    pre_configure = (
        "cat > config.over <<EOF\n"
        'osvers="gnulinux"\n'
        'myuname="nixpkgs"\n'
        'myhostname="nixpkgs"\n'
        'cf_by="nixpkgs"\n'
        'cf_time="$(date -d "@$SOURCE_DATE_EPOCH")"\n'
        "EOF\n"
        "\n"
        "# Compress::Raw::Zlib should use our zlib package instead of the one\n"
        "# included with the distribution\n"
        "cat > ./cpan/Compress-Raw-Zlib/config.in <<EOF\n"
        "BUILD_ZLIB   = False\n"
        f"INCLUDE      = {zlib_dev}/include\n"
        f"LIB          = {zlib_out}/lib\n"
        "OLD_ZLIB     = False\n"
        "GZIP_OS_CODE = AUTO_DETECT\n"
        "USE_ZLIB_NG  = False\n"
        f"ZLIB_INCLUDE = {zlib_dev}/include\n"
        f"ZLIB_LIB     = {zlib_out}/lib\n"
        "EOF\n"
        "# We need to do this because the bootstrap doesn't have a static libpthread\n"
        "sed -i 's,\\(libswanted.*\\)pthread,\\1,g' Configure\n"
    )

    return mk_derivation(
        pname="perl",
        version="5.40.0",
        builder=f"{bt}/bin/bash",
        stdenv=stdenv,
        output_names=["out", "man", "devdoc"],
        deps=[bootstrap_tools, src, zlib, glibc_bootstrap_files, gcc_wrapper],
        # zlib has 3 outputs (dev, out, static) but perl only uses dev+out
        input_drvs={zlib.drv_path: ["dev", "out"]},
        srcs=[
            PERL_CVE_2024_56406,
            PERL_CVE_2025_40909,
            PERL_NO_SYS_DIRS,
            PERL_FIX_C_LOCALE,
            PERL_SETUP_HOOK,
        ],
        env={
            "NIX_MAIN_PROGRAM": "perl",
            "configureFlags": (
                "-de"
                f" -Dprefix={placeholder('out')}"
                f" -Dman1dir={placeholder('out')}/share/man/man1"
                f" -Dman3dir={placeholder('out')}/share/man/man3"
                " -Dcc=cc"
                " -Duseshrplib"
                " -Uinstallusrbinperl"
                " -Dinstallstyle=lib/perl5"
                f" -Dlocincpth={glibc}/include"
                f" -Dloclibpth={glibc}/lib"
                " -A clear:d_crypt_r"
            ),
            "configurePlatforms": "",
            "configureScript": f"{bt}/bin/bash ./Configure",
            "disallowedReferences": gcc_w,
            "dontAddPrefix": "1",
            "dontAddStaticConfigureFlags": "1",
            "enableParallelBuilding": "",
            "patches": patches,
            "postConfigure": "",
            "postInstall": post_install,
            "postPatch": (
                'substituteInPlace dist/PathTools/Cwd.pm \\\n'
                '  --replace "/bin/pwd" "$(type -P pwd)"\n'
                "unset src\n"
            ),
            "preConfigure": pre_configure,
            "setOutputFlags": "",
            "setupHook": PERL_SETUP_HOOK,
            "src": str(src),
            "strictDeps": "1",
        },
    )
