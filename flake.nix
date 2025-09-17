# Based on <https://github.com/the-nix-way/dev-templates/blob/main/python/flake.nix>.
{
    description = "process_podcast flake";

    inputs = {
        nixpkgs.url = "github:nixos/nixpkgs/nixos-25.05";
    };

    outputs = { self, nixpkgs }:
    let
        supportedSystems = [ "x86_64-linux" "aarch64-linux" "x86_64-darwin" "aarch64-darwin" ];
        forEachSupportedSystem = f: nixpkgs.lib.genAttrs supportedSystems (system: f {
            pkgs = import nixpkgs { inherit system; };
        });
    in {
        devShells = forEachSupportedSystem ({ pkgs }: {
            default = pkgs.mkShell rec {
                name = "Process podcast";
                venvDir = "./.process_podcast";
                packages = with pkgs; [
                    python3
                    python3Packages.ipython
                    python3Packages.venvShellHook
                    python3Packages.pexpect
                    python3Packages.ptyprocess
                    python3Packages.pyparsing
                ];
                # postVenvCreation = ''
                #     pip install -r ${./requirements.txt}
                # '';
                shellHook = ''
                    venvShellHook
                '';
            };
        });
    };
}
