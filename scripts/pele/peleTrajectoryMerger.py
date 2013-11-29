import os
import sys
import optparse
import subprocess

def get_number_of_frames(pdb_file):
    """
    Uses egrep to count the number of times MODEL appears in the trajectory file, which will be indeed
    the number of different structures.
    """
    process = subprocess.Popen(["egrep","-c",''"^MODEL"'',pdb_file],stdout=subprocess.PIPE)
    lines = process.stdout.readlines()
    return int(lines[0])

def write_a_model(file_handler, current_model, out_file_handler, store_remarks):
    """
    Precondition: All 'MODEL' tag has a 'ENDMDL' tag.
    """
    # Find initial tag   
    l = file_handler.readline()
    while not l[:5]== "MODEL":
        # If we want to keep remarks, write them down
        if store_remarks and l[:6] == "REMARK":
            out_file_handler.write(l)
        l = file_handler.readline()
        
    # Once the model tag is found... write it down
    out_file_handler.write("MODEL"+str(current_model).rjust(9)+"\n")
        
    # Then write everything 'till the ENDMDL tag    
    l = file_handler.readline()
    while not l[:6]=="ENDMDL":
        out_file_handler.write(l)
        l = file_handler.readline()
    out_file_handler.write("ENDMDL\n")

def get_number_of_complete_models(pdb_file):
    process = subprocess.Popen(["egrep","-c",''"^ENDMDL"'',pdb_file],stdout=subprocess.PIPE)
    lines = process.stdout.readlines()
    return int(lines[0])
    
if __name__ == '__main__':
    
    parser = optparse.OptionParser(usage='%prog -p <arg> -o <arg> [-d <arg>]',
                                   version='1.0')
    parser.add_option('-p', action="store", dest = "traj_prefix",help="The prefix of the trajectory files to be merged.",metavar = "traj_")
    parser.add_option('-d', action="store", dest = "directory", default = "./", help="Directory where the trajectories are.",metavar = "./my_trajectories/")
    parser.add_option('-o', action="store", dest = "out_file",help="Name of the merged trajectory.",metavar = "trajectory.pdb")
    parser.add_option('--remarks', action="store_true", dest = "remarks", help="Wheter if keep remarks or not.")
    parser.add_option('--skip_first', action="store", default = -1, dest = "skip_first", metavar = "1", help="Skip the first N frames of every trajectory.")
    parser.add_option('--merge_action', action = "store", 
                                    default = "SEQUENTIAL", 
                                    dest = "merge_action", 
                                    metavar = "1", 
                                    help="Skip the first N frames of every trajectory.")
    
    options, args = parser.parse_args()
    
    # Possible errors
    merge_actions = ["SEQUENTIAL","ENTANGLE"]
    if not options.merge_action in merge_actions:
        parser.error("Please choose one option in %s for the 'merge_action' parameter."%merge_actions)
    
    # Mandatory options
    if (not options.traj_prefix) or (not options.out_file):
        parser.error("Please specify the prefix (-p) and output trajectory file (-o).")
    
    # Pick files 
    traj_file = []
    files=os.listdir(options.directory) 
    for filename in files:
        if options.traj_prefix in filename:
            traj_file.append(os.path.join(options.directory,filename))
    file_out=open(options.out_file,'w')
    traj_file.sort()
    
    if options.skip_first != -1:
        skip_out = open(options.out_file+".skipped","w")

    models_left = []
    total_files = len(traj_file)
    total_models = 0
    total_complete_models = 0
    pdb_file_handlers = []
    print "Discovering files"
    for pdb_filename in traj_file:
        number_of_models = get_number_of_frames(pdb_filename)
        number_of_complete_models = get_number_of_complete_models(pdb_filename)
        print "file:",pdb_filename,"frames:",number_of_models,"(%d)"%(number_of_complete_models)
        models_left.append(number_of_complete_models)
        total_models = total_models + number_of_models
        total_complete_models += number_of_complete_models
        pdb_file_handlers.append({
                                  'handler':open(pdb_filename,'r'),
                                  'models':number_of_models, 
                                  'complete_models':number_of_complete_models
                                  })
    
    print "Total number of models:",total_models
    print "Total number of complete models:",total_complete_models

    current_model = 0
    
    if options.merge_action == "ENTANGLE":
        """
        Entangle mode adds one model of each input trajectory to the output trajectory file
        while there are models left in those trajectories.
        """
        # While there's any model left...
        while current_model < total_complete_models:
            # For each of the files write the next model
            for i in range(len(pdb_file_handlers)):
                if models_left[i] > 0:
                    sys.stdout.flush()
                    write_a_model(pdb_file_handlers[i]['handler'], current_model, file_out, options.remarks)
                    current_model = current_model + 1
                    models_left[i] = models_left[i] - 1
                    
                    if current_model % 1000 == 0 :
                        print "Starting to process frame number", current_model
                        sys.stdout.flush()
    
    elif options.merge_action == "SEQUENTIAL":
        """
        Adds all the models of each input trajectory to the main output trajectory, skipping 
        the first N ones if necessary
        """
        for i in range(len(pdb_file_handlers)):
            for j in range(pdb_file_handlers[i]['complete_models']):
                sys.stdout.flush()
                if not (options.skip_first != -1 and j in range(0, int(options.skip_first))):
                    write_a_model(pdb_file_handlers[i]['handler'], current_model, file_out, options.remarks)
                    current_model = current_model + 1
                    if current_model % 1000 == 0 :
                        print "Starting to process frame number", current_model
                        sys.stdout.flush()
                else:
                    # Write it somewhere else
                    write_a_model(pdb_file_handlers[i]['handler'], current_model, skip_out, options.remarks)
    file_out.close()
    print "%d frames written (skipped)."%current_model, total_complete_models-current_model      