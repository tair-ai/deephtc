
# coding: utf-8

# # created on Feb 18 2018

# In[1]:


import os


from Utilities import get_time_str, decorated_os_rename

from Submit_and_Kill_job import Job_management

from Error_checker import Write_and_read_error_tag
from Error_checker import Vasp_Error_Saver
from Error_checker import Queue_std_files
from Error_checker import Vasp_Error_checker


# In[2]:


def check_calculations_status(cal_folder):
    """
    Check the status of all calculations under folder cal_folder 
    input argument:
        - cal_folder (str): Under cal_folder, a sub-folder will be created where a set of DFT calculations defined by workflow will be made.
                        Note that the absolute path should be provided.
    return a dictionary having keys below:
        - ready_folder_list (list): a list of absolute pathes where the calculations are ready.
                                    Note that the pathes where instead file __prior_ready__ exists will be put at the beginning
                                    of list read_folder_list.
        - running_folder_list (list): a list of absolute pathes where the calculations are ongoing.
        - done_folder_list (list): a list of absolute pathes where the calculations are done.
        - error_folder_list (list): a list of absolute pathes where the calculations encounter errors.
        - killed_folder_list (list): a list of absolute pathes where the calculation has been killed.
        - manual_folder_list (list): a list of absolute pathes where the error can not be fixed automatically.
        - vis_folder_list (list): a list of absolute pathes where the input files for calculations need to be prepared
    """
    signal_file_list = ["__manual__", "__test__", "__vis__", "__skipped__", "__ready__", "__prior_ready__", 
                        "__error__", "__running__", "__done__", "__killed__"]
    job_status_folder_list = ["manual_folder_list", "test_folder_list", "vis_folder_list", "skipped_folder_list", 
                              "ready_folder_list", "prior_ready_folder_list", "error_folder_list", "running_folder_list", 
                              "done_folder_list", "killed_folder_list", "other_folder_list"]
    job_status_dict = {key: [] for key in job_status_folder_list}
    if not os.path.isdir(cal_folder):
        return job_status_dict
        
    mater_folder_list = os.listdir(cal_folder)
    firework_folder_list = []
    for mater_folder in mater_folder_list:
        mater_folder_path = os.path.join(cal_folder, mater_folder)
        #in case any file appears in cal_folder.
        if not os.path.isdir(mater_folder_path):
            continue
        #ignore irrelevant files or folders
        firework_name_list = [firework_name for firework_name in os.listdir(mater_folder_path) if firework_name.startswith("step")]
        firework_folder_list += [os.path.join(mater_folder_path, firework_name) for firework_name in firework_name_list]
    
    #categorize fireworks
    for firework_folder in firework_folder_list:
        firework_belongs_to_other = True
        for signal_file_ind, signal_file in enumerate(signal_file_list):
            if os.path.isfile(os.path.join(firework_folder, signal_file)):
                job_status_dict[job_status_folder_list[signal_file_ind]].append(firework_folder)
                firework_belongs_to_other = False
                break
        if firework_belongs_to_other:
            job_status_dict["other_folder_list"].append(firework_folder)
       
    return job_status_dict


# In[3]:


def update_running_jobs_status(running_jobs_list, workflow):
    """
    Update jobs's status. for the running jobs, if any errors are detected, change __running__ to __error__ and 
        the error type will be written into __error__.
    input arguments:
        - running_jobs_list (list): a list of absolute pathes of running jobs.
        - workflow:  the output of func Parse_calculation_workflow.parse_calculation_workflow
    """
    #Check_after_cal = ["__electronic_divergence__", "__positive_energy__", "__ionic_divergence__"]
    #Check_on_the_fly = ["__electronic_divergence__", "__positive_energy__"]
    
    job_status_str = Job_management.check_jobs_in_queue_system(workflow=workflow, return_a_str=True)
    #print()
    #print(get_time_str())
    #print(job_status_str)
    #job_status_str = ""
    #if job_status_list:
    #    for i in range(1, len(job_status_list)):
    #        job_status_str += job_status_list[i]
    
    for job_path in running_jobs_list:
        
        
        find_error = False
        if Queue_std_files(cal_loc=job_path, workflow=workflow).find_std_files() != [None, None]:
            #for func Vasp_Error_checker, error_type=["after_cal"] will automatically check errors after cal.
            #If found, __running__ --> __error__ and the error info will be written into __error__ and return False
            #If not found, return True
            if Vasp_Error_checker(error_type=["after_cal"], cal_loc=job_path, workflow=workflow):
                log_txt_loc, firework_name = os.path.split(job_path)
                with open(os.path.join(log_txt_loc, "log.txt"), "a") as f:
                    f.write("{} INFO: Calculation successfully finishes at {}\n".format(get_time_str(), firework_name))
                    f.write("\t\t\t__running__ --> __done__\n")
                    decorated_os_rename(loc=job_path, old_filename="__running__", new_filename="__done__")
                    #os.rename(os.path.join(job_path, "__running__"), os.path.join(job_path, "__done__"))
        else:
            #for func Vasp_Error_checker, error_type=["on_the_fly"] will automatically check errors on the fly.
            #If found, __running__ --> __error__ and the error info will be written into __error__ and return False
            #If not found, return True
            Vasp_Error_checker(error_type=["on_the_fly"], cal_loc=job_path, workflow=workflow)
            
        if os.path.isfile(os.path.join(job_path, "__running__")):
            if Queue_std_files(cal_loc=job_path, workflow=workflow).find_std_files() != [None, None]:
                continue
                
            
                    
                
            queue_id = Job_management(cal_loc=job_path, workflow=workflow).find_queue_id()
            #print(queue_id, queue_id in job_status_str)
            if queue_id not in job_status_str:
                if not os.path.isfile(os.path.join(cal_loc, "__no_of_times_not_in_queue__")):
                    with open(os.path.join(cal_loc, "__no_of_times_not_in_queue__"), "w") as f:
                        f.write("1")
                else:
                    with open(os.path.join(cal_loc, "__no_of_times_not_in_queue__"), "r") as f:
                        times = int(next(f).strip())
                    if times <= 5:
                        with open(os.path.join(cal_loc, "__no_of_times_not_in_queue__"), "w") as f:
                            f.write(str(times+1))
                        continue
                
                log_txt_loc, firework_name = os.path.split(job_path)
                with open(os.path.join(log_txt_loc, "log.txt"), "a") as f:
                    f.write("{} Queue Error: {}\n".format(get_time_str(), job_path))
                    f.write("\t\t\tThe running job is not found in queue.\n")
                    f.write("\t\t\t__running__ --> __manual__\n")
                    f.write("\t\t\tCreate file __running_job_not_in_queue__.\n")
                    open(os.path.join(job_path, "__running_job_not_in_queue__"), "w").close()
                    decorated_os_rename(loc=job_path, old_filename="__running__", new_filename="__manual__")
                    #os.rename(os.path.join(job_path, "__running__"), os.path.join(job_path, "__manual__"))                
            else:
                if os.path.isfile(os.path.join(cal_loc, "__no_of_times_not_in_queue__")):
                    os.remove(os.path.join(cal_loc, "__no_of_times_not_in_queue__"))


# In[4]:


def update_killed_jobs_status(killed_jobs_list, workflow, max_error_times=5):
    """
    Update killed jobs's status. If the error in __killed__ can be fixed, fix it and __killed__ --> __ready__; 
        Ohterwise __killed__ --> __manual__
    input arguments:
        - killed_jobs_list (list): a list of absolute pathes of killed jobs.
        - workflow:  the output of func Parse_calculation_workflow.parse_calculation_workflow
        - max_error_times (int): the maximum error times. Beyond this value, __killed__ --> __manual__. Default: 5
    """
    
    #Error_type_dict = ["__unfinished_OUTCAR__", "__electronic_divergence__", 
    #                   "__ionic_divergence__", "__positive_energy__"]
    
    for killed_job in killed_jobs_list:
        #The killed job won't be processed until the stdout & stderr files of the queue system appear.
        if Queue_std_files(cal_loc=killed_job, workflow=workflow).find_std_files() == [None, None]:
            continue
        
        error_type = Write_and_read_error_tag(killed_job).read_error_tag("__killed__")
        error_checker = Vasp_Error_checker(cal_loc=killed_job, error_type=error_type, workflow=workflow)
        log_txt_loc, firework_name = os.path.split(killed_job)
        if Vasp_Error_Saver(cal_loc=killed_job, workflow=workflow).find_error_times() >= max_error_times:
            decorated_os_rename(loc=killed_job, old_filename="__killed__", new_filename="__manual__")
            #os.rename(os.path.join(killed_job, "__killed__"), os.path.join(killed_job, "__manual__"))
            with open(os.path.join(log_txt_loc, "log.txt"), "a") as f:
                f.write("{} Killed: {}\n".format(get_time_str(), killed_job))
                f.write("\t\t\tThe error times hit the max_error_times ({})\n".format(max_error_times))
                f.write("\t\t\t__killed__ -> __manual__\n")
        elif error_checker.correct():
            #Queue_std_files(cal_loc=killed_job, workflow=workflow).remove_std_files()
            #to_be_removed = ["OUTCAR", "OSZICAR", workflow[0]["vasp.out"]]
            #for file_ in to_be_removed:
            #    if os.path.isfile(os.path.join(killed_job, file_)):
            #        os.remove(os.path.join(killed_job, file_))
                    
            os.remove(os.path.join(killed_job, "__killed__"))
            open(os.path.join(killed_job, "__ready__"), "w").close()
            with open(os.path.join(log_txt_loc, "log.txt"), "a") as f:
                f.write("{} Killed: Successfully correct the error {} under {}\n".format(get_time_str(), error_type, firework_name))
                #f.write("\t\t\tremove stdout and stderr files\n")
                #for file_ in to_be_removed:
                #    f.write("\t\t\tremove {}\n".format(file_))
                f.write("\t\t\t__killed__ --> __ready__\n")
            
        else:
            decorated_os_rename(loc=killed_job, old_filename="__killed__", new_filename="__manual__")
            #os.rename(os.path.join(killed_job, "__killed__"), os.path.join(killed_job, "__manual__"))
            with open(os.path.join(log_txt_loc, "log.txt"), "a") as f:
                f.write("{} Killed: Fail to correct the error {} under {}\n".format(get_time_str(), error_type, firework_name))
                f.write("\t\t\t__killed__ --> __manual__\n")
            
    

