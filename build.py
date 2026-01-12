from pathlib import Path
from argparse import ArgumentParser
from importlib import util
from collections import OrderedDict
import logging

RED = "\033[91m"
YELLOW = "\033[93m" 
RESET = "\033[0m"   

KeyFiles = OrderedDict( [
    ("grf.pnml", "\"grf.pnml\" not found. It should be in \"src\" and contain the grf block."),
    ("railtypes.pnml", "\"railtypes.pnml\" not found. It should be in \"src\" and contain the railtypetable block."),
    ("sounds.pnml", "\"sounds.pnml\" not found.  Assuming no sounds are required"),
    ("templates_shared.pnml", "\"templates_shared.pnml\" not found.  Assuming no templates are required"),
    ("templates_trains.pnml", "\"templates_trains.pnml\" not found.  Assuming no templates are required"),
    # ("templates_trams.pnml", "\"templates_trams.pnml\" not found.  Assuming no templates are required"),
] )

SpecialOrderFiles = { 
    "BR_Mk3_TS.pnml": ["BR_Mk3_TSD.pnml", "BR43.pnml", "BR253.pnml","BR254.pnml", "BR256.pnml", "BR257.pnml"],
    "BR_Mk4_Header.pnml": ["BR_Mk4_DVT.pnml", "BR_Mk4_TF.pnml", "BR_Mk4_TFE.pnml", "BR_Mk4_TRFB.pnml", "BR_Mk4_TRSB.pnml", "BR_Mk4_TS.pnml", "BR_Mk4_TSD.pnml", "BR_Mk4_TSE.pnml", "BR91.pnml", "BR91_IC225.pnml"],
    "Containers_BR.pnml": ["BR_Conflat_A.pnml", "BR_Conflat_P.pnml"],
    "RCH_1907_graphics.pnml": ["1_Plank_Open_Wagons_Load.pnml", "3_Plank_Open_Wagons_Load.pnml", "5_Plank_Open_Wagons_Load.pnml", "7_Plank_Open_Wagons_Load.pnml", "RCH_1907.pnml", "RCH_1907_1_plank.pnml", "RCH_1907_3_plank.pnml", "RCH_1907_5_plank.pnml", "RCH_1907_7_plank.pnml", "RCH_1907_Van.pnml"],
    "60Long_Cont20_Side.pnml": ["60Long_Cont30_Side.pnml", "60Long_Cont40_Side.pnml", "BR_FFA.pnml","BR_FEA.pnml"],
    "LMS_4F.pnml" : ["MR_Tenders.pnml", "MR_3835.pnml", "LMS_Fowler_2P.pnml", "LMS_Fowler_4P.pnml",],
    "Evol_Header.pnml": ["Evol_B.pnml", "Evol_F.pnml", "Evol_T.pnml"]
}

def check_project_structure(src_directory: Path, gfx_directory: Path,
                            lang_directory: Path):
    has_lang_dir = True

    # Check that the project is properly structured
    if not src_directory.exists():
        raise FileNotFoundError("\"src\" directory not found.  Aborting")
    if not gfx_directory.exists():
        raise FileNotFoundError("\"gfx\" directory not found.  Aborting")
    if not lang_directory.exists():
        logging.warning("\"lang\" directory not found.  Assuming hard-coded strings (this is not best practice)")
        has_lang_dir = False

    # iterate over KeyFiles, and ensure they exist
    for file, error in KeyFiles.items():
        if not src_directory.joinpath(file).exists():
            if file == "grf.pnml" or file == "railtypes.pnml":
                raise FileNotFoundError(error)
            else:
                logging.warning(f"{error}")

    logging.info("Project structure is correct\n")
    return has_lang_dir


def find_special_file(filename:str, search_dir: Path):
    matches = list(search_dir.rglob(filename))
    
    if len(matches) == 0:
        raise FileNotFoundError(f"No file named '{filename}' found")
    elif len(matches) > 1:
        raise RuntimeError(f"Multiple files named '{filename}' found: {matches}")
    
    return matches[0]

def copy_file(filepath: Path, nml_file: str):
    # If the pnml filepath doesn't exist, exit
    if not filepath.exists():
        raise FileNotFoundError(f"The file <{filepath}> does not exist.")

    # Read the pnml file into the internal nml
    with open(str(filepath), "r") as file:
        nml_file += "// " + filepath.stem + filepath.suffix + "\n"
        for line in file:
            nml_file += line
    nml_file += "\n\n"
    return nml_file


def write_file(filename: str, nml_file: str):
    from os import makedirs
    # Generate the filepath and check if it exists
    filepath = Path("build/" + filename + ".nml")
    build_dir = Path("build/")
    if not build_dir.exists():
        makedirs("build")

    if filepath.exists():
        logging.info("'%s.nml' already exists.  Overwriting" % filename)

    # Write the internal nml to the file
    with open(filepath, "w") as file_writer:
        for line in nml_file:
            file_writer.write(line)

    logging.info("Written all files to '%s.nml' file\n" % filename)


def compile_grf(has_lang_dir, grf_name, lang_dir):
    # Check if we have the nml package
    found_nml = util.find_spec("nml")
    if found_nml is not None:
        # Import nml's main module
        import nml.main # type: ignore
        parameters = []
        if has_lang_dir:
            # If we have a lang directory, add it to the parameters
            parameters = ["--lang", str(lang_dir), "build/" + grf_name + ".nml"]
        else:
            # If not, just the nml name
            parameters = ["build/" + grf_name + ".nml"]
        try:
            # Try to compile the nml file
            nml.main.main(parameters)
            logging.info("Finished compiling grf file\n")
        except SystemExit:
            # nml uses sys.exit(), so catch this to stop the program exiting
            logging.info("nml tried to exit but was stopped")
    else:
        # nml isn't installed
        logging.warning("nml is not installed.  You can get it using 'pip install nml'")


def run_game(grf_name):
    from sys import platform

    logging.info("Detecting platform")

    # Change default paths depending on whether we use Linux or Windows (sorry OSX)
    if platform.startswith("linux"):
        newgrf_dir = Path.home().joinpath(".openttd", "newgrf")
        executable_path = "/usr/bin/openttd"
        kill_cmd = ["killall","openttd"]
        logging.info("Detected as Linux")
    elif platform.startswith("win32"):
        newgrf_dir = Path.home().joinpath("Documents", "OpenTTD", "newgrf")
        executable_path = "C:/Program Files/OpenTTD/openttd.exe"
        kill_cmd = ["taskkill.exe" "/IM" "OpenTTD.exe"]
        logging.info("Detected as Windows")
    else:
        logging.warning("Detected as Other.  Cannot run game.")

    logging.info("Attempting to read config")
    json_read_ok = False
    # Check that the config file exists
    if Path("build/build.json").exists():
        from json import load, decoder
        with open("build/build.json") as json_data:
            # Try to read the config file
            try:
                data = load(json_data)
            # Errors if the file in invalid
            except decoder.JSONDecodeError:
                logging.error("The config file is invalid")
                json_read_ok = False
            else:
                # Read successfully
                # Try to read the keys from the json file
                try:
                    newgrf_dir = data["newgrf_dir"]
                    executable_path = data["executable"]
                # Errors if not all keys are found
                except KeyError:
                    logging.error("The config json file is invalid")
                    json_read_ok = False
                # Read successfully, set read_ok to true
                else:
                    json_read_ok = True
                    logging.info("Read config successfully")

    # If reading the json didn't work
    if not json_read_ok:
        from json import dump
        from os import access, X_OK

        logging.info("No config, require user input")

        # Prompt the user for the "newgrf" directory until we get something like it
        while not Path(newgrf_dir).exists():
            newgrf_dir = input("Enter the newgrf directory: ")
            if len(newgrf_dir) > 6:
                newgrf_dir = "~/.openttd/newgrf"
                continue
            if newgrf_dir[-6:] != "newgrf":
                newgrf_dir = "~/.openttd/newgrf"

        # Prompt the user for the executable path until we get an executable
        while not Path(executable_path).exists():
            executable_path = input("Enter the OpenTTD executable path: ")
            if not (access(executable_path, X_OK)):
                executable_path = "/usr/bin/openttd"

        # Dump the two paths to a json file for next time
        with open("build/build.json", "w") as json_data:
            data = {
                "newgrf_dir": str(newgrf_dir),
                "executable": str(executable_path)
            }
            dump(data, json_data)

    from shutil import copy
    from subprocess import Popen
    from os import devnull

    # Kill existing processes
    logging.info("Killing existing processes")
    try:
        kill_process = Popen(kill_cmd)
        kill_process.wait()
    except:
        logging.warning("Something went wrong when trying to kill processes")

    # Copy grf
    logging.info("Copying grf")
    copy("build/" + grf_name + ".grf", Path(newgrf_dir))

    # Run the game in it's root directory
    logging.info("Running game\n")
    # Redirect stdout and stderr
    null = open(devnull, "w")
    Popen([executable_path, "-t", "2050", "-g"], cwd=Path(executable_path).parent, stdout=null, stderr=null)


def main(grf_name, src_dir, lang_dir, gfx_dir, b_compile_grf, b_run_game, logging_level=logging.INFO):
    logger = logging.getLogger()
    logger.setLevel(logging_level)
    
    src_directory = Path("src")
    lang_directory = Path("lang")
    gfx_directory = Path("gfx")

    nml_file = ""
    has_lang_dir = False

    # Check if the project is set up properly and we have a lang directory
    has_lang_dir = check_project_structure(src_directory, gfx_directory, lang_directory)

    # Add the special files to the internal nml file
    for files in KeyFiles.keys():
        nml_file = copy_file(src_directory.joinpath(files), nml_file)

    # Get a list of all the pnml files in src
    file_list = dict()
    pnml_files = OrderedDict( [ ("Top level", list()), ("Priority", list()), ("Normal", list()), ("Append", list()) ] )
    tender_files = dict()
    special_files = dict()
    in_chain = set()

    for file in src_directory.rglob("*.pnml"):
        relative_path = file.relative_to(src_directory)
        file_name = file.stem + file.suffix # e.g. BR43.pnml

        if file.parent not in file_list.keys():
            file_list[file.parent] = list()

        if (file_name) not in KeyFiles.keys():
            file_list[file.parent].append(file)

        if file_name in SpecialOrderFiles and file_name not in in_chain:
            chain = SpecialOrderFiles.get(file_name)
            file_chain = []
            if type(chain) is str:
                in_chain.add(chain)
                file_chain.append(find_special_file(chain, src_directory))
            elif type(chain) is list:
                for cf in chain:
                    in_chain.add(cf)
                    file_chain.append(find_special_file(cf, src_directory))
            elif chain is None:
                raise RuntimeError

            special_files[file_name] = file_chain

        # sort and add the pnml files to their correct location
        if len(relative_path.parts) == 1:
            if (file_name not in KeyFiles.keys()): # filter out the KeyFiles
                pnml_files["Top level"].append(file)
        elif "priority" in relative_path.parts:
            pnml_files["Priority"].append(file)
        elif "append" in relative_path.parts:
            pnml_files["Append"].append(file)
        elif "Tenders" in file.stem:
            company_name = file.stem.rsplit("_")[0]
            tender_files[company_name] = file
        elif file_name not in KeyFiles and file_name not in in_chain:
            pnml_files['Normal'].append(file)
  

    f = lambda a: "src" if a == src_directory else "/".join(directory.parts[1:])
    for directory in file_list.keys():
        logging.debug(f"Found in directory [{f(directory)}]:")
        logging.debug([str(file.stem + file.suffix) for file in file_list[directory]])

    logging.info("Finished finding pnml files\n")

    # iterate over all pnml files in the dictionary, and append it to the nml file
    for key, file_list in pnml_files.items():
        logging.debug(f"Starting to read {key} files")
        
        for file in sorted(file_list):
            file_name = file.stem + file.suffix

            if file_name in in_chain:
                continue

            if "Locomotive_Steam" in file.parts:
                engine_company_name = file.stem.rsplit("_")[0]
                if engine_company_name in tender_files:
                    tender_file = tender_files.pop(engine_company_name)
                    logging.debug(f"Reading Tender file: {tender_file.stem + tender_file.suffix}")
                    nml_file = copy_file(tender_file, nml_file)

            logging.debug(f"Reading {key} file: {file_name}")
            nml_file = copy_file(file, nml_file)

            if file_name in SpecialOrderFiles.keys():
                chain = special_files.get(file_name)
                if chain is not None:
                    for chain_file in chain:
                        logging.debug(f"Reading Special Order file: {chain_file.stem + chain_file.suffix}")
                        nml_file = copy_file(chain_file, nml_file)

    logging.info("Copied all files to internal buffer\n")

    # Write the internal nml to a file
    write_file(grf_name, nml_file)

    # If we're compiling or running the game
    if b_compile_grf or b_run_game:
        # Try to compile the GRF
        compile_grf(has_lang_dir, grf_name, lang_directory)

    # Optionally run the game
    if b_run_game:
        return run_game(grf_name)


if __name__ == "__main__":
    # Parser arguments
    parser = ArgumentParser(description="Compile pnml files into one nml file")
    parser.add_argument("grf_name")
    parser.add_argument("--src", default="src", help="Source files directory")
    parser.add_argument("--lang",
                        default="lang",
                        help="Language files directory")
    parser.add_argument("--gfx",
                        default="gfx",
                        help="Graphics files directory")
    parser.add_argument("--compile",
                        action="store_true",
                        help="Compile the nml file with nmlc")
    parser.add_argument(
        "--run",
        action="store_true",
        help="Run the game after compilation (will also compile the file.  Also kills existing instances)")
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--quiet", 
        action="store_const", 
        dest="log_level", 
        const=logging.ERROR )
    group.add_argument(
        "--debug", 
        action="store_const", 
        dest="log_level", 
        const=logging.DEBUG )

    parser.set_defaults(log_level=logging.INFO)
    args = parser.parse_args()

    # Reports any errors in the nml file compilation process
    main(args.grf_name, args.src, args.lang, args.gfx,
                      args.compile, args.run, args.log_level)
    
    # if error_code == -1:
    #     print(
    #         "The nml file failed to compile properly.  Please consult the log")
    # elif error_code == -2:
    #     print("The nml file compiled correctly, but nml failed to compile it")
    # elif error_code == -3:
    #     print(
    #         "The grf file compiled successfully but the game failed to start")
    # elif error_code == 1:
    #     print("The grf file was compiled successfully")
    # elif error_code == 2:
    #     print(
    #         "The grf file was compiled successfully, and the game was started")
    # else:
    #     print("The nml file was compiled successfully (this is the not grf)")
