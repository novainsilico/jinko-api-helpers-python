{
  description = "Jinko API Helper Python Package";
  inputs.flake-utils.url = "github:numtide/flake-utils";
  inputs.nixpkgs.follows = "dream2nix/nixpkgs";
  inputs.dream2nix.url = "github:nix-community/dream2nix";
  outputs =
    { self
    , flake-utils
    , nixpkgs
    , dream2nix
    , ...
    } @ inputs:
    flake-utils.lib.eachSystem
      [
        flake-utils.lib.system.x86_64-linux
      ]
      (
        system:
        let
          pkgs = import nixpkgs { inherit system; };
          shellBuildInputs = [
            # Poetry is the default package manager for the cookbook project
            pkgs.poetry
            # Add interactive bash to support `poetry shell`
            pkgs.bashInteractive
            pkgs.curl
            pkgs.just
          ];
          shellInit = ''
            export LD_LIBRARY_PATH=${pkgs.lib.makeLibraryPath [
              pkgs.stdenv.cc.cc
            ]}
            export POETRY_CACHE_DIR="$(pwd)/.cache/pypoetry"
            source .envrc
          '';
        in
        {
          packages = {
            jinkoEnv = dream2nix.lib.evalModules {
              packageSets.nixpkgs = nixpkgs.legacyPackages.${system};
              modules = [
                dream2nix.modules.dream2nix.WIP-python-pyproject
                ({ config, ... }: {
                  deps = {nixpkgs, ...}: {
                    python = nixpkgs.python312;
                    poetry = nixpkgs.poetry;
                  };

                  public.pythonWithEnv = config.deps.python.withPackages (_: config.mkDerivation.propagatedBuildInputs);
                  mkDerivation.src = ./jinko_env;
                  paths.projectRoot = ./.;
                  paths.package = "jinko_env";
                  # Not sure how to properly build a folder, so we turn
                  # it into a whl file which is the known case
                  pip.overrides.jinko-sdk.mkDerivation.src = let
                    pyproject = builtins.fromTOML (builtins.readFile ./pyproject.toml);
                    filename = "jinko_sdk-${pyproject.tool.poetry.version}-py${config.deps.python.sourceVersion.major}-none-any.whl";
                  in pkgs.runCommand filename {} ''
                    HOME=$(pwd)
                    cd ${./.}
                    ${config.deps.poetry}/bin/poetry build -o $HOME/dist
                    cp $HOME/dist/${filename} $out
                  '';
                })
              ];
            };
          };
          # Default shell with only poetry installed
          devShells = {
            default = pkgs.mkShell {
              name = "default";
              buildInputs = shellBuildInputs;
              shellHook = ''
                ${shellInit}
              '';
            };

            # Install and load a poetry shell
            poetry = pkgs.mkShell {
              buildInputs = shellBuildInputs;
              shellHook = ''
                ${shellInit}
                poetry install
                eval $(poetry env activate)
              '';
            };

            jinkoEnv = pkgs.mkShell {
              buildInputs = [
                pkgs.bashInteractive
                self.packages.${system}.jinkoEnv.pythonWithEnv 
              ];
            };
          };
        }
      );
}
