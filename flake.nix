{

  inputs.nixpkgs.url = github:nixos/nixpkgs/nixos-24.11;

  outputs = inputs:
    let
      system = "x86_64-linux";
      pkgs = import inputs.nixpkgs { inherit system; };
      dev-shell = pkgs.mkShell {
        nativeBuildInputs = [
          pkgs.pkg-config
          (pkgs.python3.withPackages (pp: with pp; [ ipython pkgconfig ]))
        ];
        buildInputs = [ pkgs.nix.dev ];
      };
    in
      {
        devShells.${system}.default = dev-shell;
      };

}
