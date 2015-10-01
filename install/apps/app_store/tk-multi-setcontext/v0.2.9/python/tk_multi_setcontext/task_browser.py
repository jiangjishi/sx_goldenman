# Copyright (c) 2013 Shotgun Software Inc.
# 
# CONFIDENTIAL AND PROPRIETARY
# 
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit 
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your 
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights 
# not expressly granted therein are reserved by Shotgun Software Inc.

import tank
import os
import sys
import threading

from tank.platform.qt import QtCore, QtGui

browser_widget = tank.platform.import_framework("tk-framework-widget", "browser_widget")


class TaskBrowserWidget(browser_widget.BrowserWidget):

    
    def __init__(self, parent=None):
        browser_widget.BrowserWidget.__init__(self, parent)
        
        # only load this once!
        self._current_user = None
        self._current_user_loaded = False
        
        # create an action for grabbing tasks
        
    def grab_task(self):
        
        try:
            task_id = self.sender().parent().sg_data["id"]
            task_assignees = self.sender().parent().sg_data["task_assignees"]
        except:
            QtGui.QMessageBox.critical(self, "Cannot Resolve Task!", "Cannot resolve this task!")            
            return
            
        res = QtGui.QMessageBox.question(self, 
                                         "Assign yourself to this task?", 
                                         "Assign yourself to this task?",
                                         QtGui.QMessageBox.Ok|QtGui.QMessageBox.Cancel)
        if res == QtGui.QMessageBox.Ok:
            task_assignees.append(self._current_user)
            self._app.shotgun.update("Task", task_id, {"task_assignees": task_assignees})
        
        # ask widget to refresh itself
        self.clear()
        self.load(self._current_data)
        
        

    def get_data(self, data):
        
        self._current_data = data
        
        if not self._current_user_loaded:
            self._current_user = tank.util.get_shotgun_user(self._app.shotgun)
            self._current_user_loaded = True
        
        
        # start building output data structure        
        output = {}
        output["associated_entity"] = data["entity"]

        if data["own_tasks_only"]:
            
            if self._current_user is None:
                output["tasks"] = []
                output["users"] = []
                
            else:
                # get my stuff
                output["users"] = [ self._current_user ]
                output["tasks"] = self._app.shotgun.find("Task", 
                                                    [ ["project", "is", self._app.context.project],
                                                      ["entity", "is", data["entity"]], 
                                                      ["task_assignees", "is", self._current_user ]], 
                                                    ["content", 
                                                     "task_assignees", 
                                                     "image", 
                                                     "sg_status_list"])
                         
        else:
            # get all tasks
            output["tasks"] = self._app.shotgun.find("Task", 
                                                [ ["project", "is", self._app.context.project],
                                                  ["entity", "is", data["entity"] ] ], 
                                                ["content", "task_assignees", "image", "sg_status_list"])
        
            # get all the users where tasks are assigned.
            user_ids = []
            for task in output["tasks"]:
                user_ids.extend( [ x["id"] for x in task.get("task_assignees", []) ] )
            
            if len(user_ids) > 0:
                # use super weird filter syntax....
                sg_filter = ["id", "in"]
                sg_filter.extend(user_ids)
                output["users"] = self._app.shotgun.find("HumanUser", [ sg_filter ], ["image"])
            else:
                output["users"] = []
        
        return output
                    
    def process_result(self, result):
        
        entity_data = result["associated_entity"]
        tasks = result["tasks"]
        
        entity_str = "%s %s" % (entity_data.get("type", "Unknonwn"), entity_data.get("code", "Unknonwn"))

        if len(tasks) == 0:
            self.set_message("No Tasks found for %s!" % entity_str)
            
        else:
            i = self.add_item(browser_widget.ListHeader)
            
            i.set_title("Tasks for %s" % entity_str)
            for d in tasks:
                i = self.add_item(browser_widget.ListItem)
                
                details = []
                details.append("<b>Task: %s</b>" % d.get("content", ""))
                
                details.append("Status: %s" % d.get("sg_status_list"))
                
                names = [ x.get("name", "Unknown") for x in d.get("task_assignees", []) ]
                names_str = ", ".join(names)
                details.append("Assigned to: %s" % names_str)
                
                i.set_details("<br>".join(details))
                
                i.sg_data = d
                i.setToolTip("Double click to set context.")
                
                # add a grab task action
                if self._current_user: # not None
                    if d.get("task_assignees"):
                        assigned_user_ids = [ x["id"] for x in d.get("task_assignees") ]
                    else:
                        assigned_user_ids = []
                        
                    if self._current_user["id"] not in assigned_user_ids:
                        # are are not assigned to this task. add ability to grab it                
                        i.grab_action = QtGui.QAction("Add %s as an assignee to this task." % self._current_user["name"], i)
                        i.grab_action.triggered.connect(self.grab_task)                       
                        i.addAction(i.grab_action)
                        i.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)                
                
                
                # finally look up the thumbnail for the first user assigned to the task
                task_assignees = d.get("task_assignees", [])
                if len(task_assignees) > 0:
                    user_id = task_assignees[0]["id"]
                    # is this user id in our users dict? In that case we have their thumb!
                    for u in result["users"]:
                        if u["id"] == user_id:
                            # if they have a thumb, assign!
                            if u.get("image"):
                                i.set_thumbnail(u.get("image"))
                            break            
        
        