{
  description = "Jinko API Helper Python Package";
  inputs.flake-utils.url = "github:numtide/flake-utils";
  inputs.nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
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
          mkJinkoEnv = env_path: name: dream2nix.lib.evalModules {
            packageSets.nixpkgs = nixpkgs.legacyPackages.${system};
            modules = [
              dream2nix.modules.dream2nix.WIP-python-pyproject
              ({ config, ... }: {
                deps = {nixpkgs, ...}: {
                  python = nixpkgs.python313;
                  poetry = nixpkgs.poetry;
                  patchelf = nixpkgs.patchelf;
                  rdma-core = nixpkgs.rdma-core;
                  fetchurl = nixpkgs.fetchurl;
                  runCommand = nixpkgs.runCommand;
                  rename = nixpkgs.rename;
                };

                public.pythonWithEnv = config.deps.python.withPackages (p: [ p.tkinter ] ++ config.mkDerivation.propagatedBuildInputs);
                mkDerivation.src = env_path;
                paths.projectRoot = ./.;
                paths.package = name;
                # Environment needed for ecos (dependency of
                # scikit-survival) during the locking
                pip.env = {
                  LD_LIBRARY_PATH = pkgs.lib.makeLibraryPath [ pkgs.stdenv.cc.cc ];
                };
                pip.overrides.vpop-calibration = {
                  buildPythonPackage.pyproject = true;
                  mkDerivation.propagatedBuildInputs = [ config.deps.python.pkgs.poetry-core ];
                };
                pip.overrides.torch.mkDerivation.preBuild = ''
                  ${config.deps.rename}/bin/rename -v "s/-2B/+/" dist/*.whl
                '';
                pip.overrides.kaleido.mkDerivation.postFixup = ''
                  sed -i -e "s@/bin/bash@/bin/sh@" $out/lib/python*/site-packages/kaleido/executable/kaleido
                  ${config.deps.patchelf}/bin/patchelf --set-interpreter "$(cat $NIX_CC/nix-support/dynamic-linker)" $out/lib/python*/site-packages/kaleido/executable/bin/kaleido
                '';
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
                # "sbmlxdf" depends on "libsbml-experimental" while "tellurium" depends on "libsbml" which 
                # generates collisions. This is fixed by telling Nix to prioritize the "libsbml-experimental"
                pip.overrides.python-libsbml.mkDerivation.meta.priority = 10;
              })
              ({ config, lib, ... }: {
                pip.overrides = let
                  deps = [
                    "autograd-gamma"
                    "ecos"
                    "freia"
                    "ndtest"
                    "odfpy"
                    "uuid"
                  ];
                in lib.genAttrs deps (_: {
                  buildPythonPackage.pyproject = true;
                  buildPythonPackage.build-system = [ config.deps.python.pkgs.setuptools ];
                });
              })
            ];
          };
        in
        {
          packages = {
            jinkoEnv = mkJinkoEnv ./jinko_env "jinko_env";
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
                pkgs.openssl.bin
              ];
            };
          };
        }
      );
}
