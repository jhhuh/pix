{

  inputs.nixpkgs.url = github:nixos/nixpkgs/nixos-24.11;

  outputs = inputs:
    let
      system = "x86_64-linux";
      pkgs = import inputs.nixpkgs { inherit system; };
      dev-shell = pkgs.mkShell {
        nativeBuildInputs = [
          (pkgs.python3.withPackages (pp: with pp; [ ipython pytest mkdocs mkdocs-material ]))
        ];
      };
    in
      {
        devShells.${system}.default = dev-shell;
      };

}
