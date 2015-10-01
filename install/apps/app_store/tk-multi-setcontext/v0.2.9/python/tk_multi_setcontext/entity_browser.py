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

class EntityBrowserWidget(browser_widget.BrowserWidget):

    
    def __init__(self, parent=None):
        browser_widget.BrowserWidget.__init__(self, parent)
        
        # only load this once!
        self._current_user = None
        self._current_user_loaded = False
        

    def get_data(self, data):
            
            
        types_to_load = self._app.get_setting("sg_entity_types", [])
            
        if not self._current_user_loaded:
            self._current_user = tank.util.get_shotgun_user(self._app.shotgun)
            self._current_user_loaded = True
        
        sg_data = []

        if data["own_tasks_only"]:

            if self._current_user is not None:
                
                # my stuff
                tasks = self._app.shotgun.find("Task", 
                                               [ ["project", "is", self._app.context.project], 
                                                 ["task_assignees", "is", self._current_user ]], 
                                                 ["entity"]
                                               )
                
                # get all the entities that are associated with entity types that 
                # we are interested in.
                entities_to_load = {}
                for x in tasks:
                    task_et_type = x["entity"]["type"]
                    if task_et_type in types_to_load:
                        if task_et_type not in entities_to_load:
                            entities_to_load[task_et_type] = []
                        entities_to_load[task_et_type].append(x["entity"]["id"])

                # now load data for those
                for et in entities_to_load:
                    item = {}
                    item["type"] = et
                    # weird syntax
                    filter = ["id", "in"]
                    filter.extend(entities_to_load[et])
                    item["data"] = self._app.shotgun.find(et, 
                                                          [ filter ], 
                                                          ["code", "description", "image"])
                    sg_data.append(item)
            
        else:
            # load all entities
            for et in types_to_load:            
                item = {}
                item["type"] = et
                item["data"] = self._app.shotgun.find(et, 
                                                      [ ["project", "is", self._app.context.project],
                                                        ["sg_status_list", "is_not", "fin" ] ], 
                                                      ["code", "description", "image"])
                sg_data.append(item)
            
        
        return {"data": sg_data}


    def process_result(self, result):

        if len(result.get("data")) == 0:
            self.set_message("No matching items found!")
            return

        for item in result.get("data"):
            i = self.add_item(browser_widget.ListHeader)
            i.set_title("%ss" % tank.util.get_entity_type_display_name(self._app.tank, item.get("type")))

            for d in item["data"]:
                i = self.add_item(browser_widget.ListItem)
                
                details = "<b>%s %s</b><br>%s" % (tank.util.get_entity_type_display_name(self._app.tank, d.get("type")), 
                                                  d.get("code"), 
                                                  d.get("description"))
                
                i.set_details(details)
                i.sg_data = d
                if d.get("image"):
                    i.set_thumbnail(d.get("image"))                

        
        