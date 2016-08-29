import arcpy
from arcpy import env, da, mapping
import os
import time
from os import path
from itertools import groupby
from operator import itemgetter
env.overwriteOutput = 1


class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Data Comparison Toolbox"
        self.alias = ""

        # List of tool classes associated with this toolbox
        self.tools = [CompareGeodatabases]


class CompareGeodatabases(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Compare Geodatabases"
        self.description = "perform analysis on the schema differences and feature differences between 2 geodatabases"
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        param0 = arcpy.Parameter(
            displayName="Outfolder",
            name="Outfolder",
            datatype="DEFolder",
            parameterType="Required",
            direction="Input"
        )
        param0.value = r"C:\ESRI_WORK_FOLDER\bcad\From TIM\CompareSchema_8_29\Comparison"

        param1 = arcpy.Parameter(
            displayName="Base GDB",
            name="BaseGDB",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input"
        )
        param1.value = r"C:\ESRI_WORK_FOLDER\bcad\From TIM\CompareSchema_8_29\Working.gdb"

        param2 = arcpy.Parameter(
            displayName="Test GDB",
            name="TestGDB",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input"
        )
        param2.value = r"C:\ESRI_WORK_FOLDER\bcad\From TIM\CompareSchema_8_29\Client.gdb"

        params = [param0, param1, param2]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        outfolder = parameters[0].valueAsText
        base_gdb = parameters[1].valueAsText
        test_gdb = parameters[2].valueAsText

        masterfolder_path = "{}\\{}".format(outfolder, "AroraChanges")
        clientfolder_path = "{}\\{}".format(outfolder, "ClientChanges")

        def feedback(severity, message):
            x, m = [severity, message]
            if x == 0:
                arcpy.AddMessage(m)
            elif x == 1:
                arcpy.AddWarning(m)
            elif x == 2:
                arcpy.AddError(m)
            print m

            return

        def CreateFileStructure(path):
            if os.path.exists(path) == False:
                os.mkdir(path)
                os.mkdir("{}\\{}".format( \
                    path, "shapeChanges"))
                arcpy.CreateFileGDB_management( \
                    "{}\\{}".format(path, "shapeChanges"), "GeosInThisNotInThat")
                os.mkdir("{}\\{}".format(path, "attrChanges"))
                arcpy.CreateFileGDB_management( \
                    "{}\\{}".format(path, "attrChanges"), "AttrsInThisNotInThat")
            else:
                if arcpy.Exists("{}\\{}".format(path, "shapeChanges")):
                    if arcpy.Exists("{}\\{}\\{}.gdb".format( \
                            path, "shapeChanges", "GeosInThisNotInThat")):
                        arcpy.Delete_management("{}\\{}\\{}.gdb".format( \
                            path, "shapeChanges", "GeosInThisNotInThat"))
                        arcpy.CreateFileGDB_management("{}\\{}".format( \
                            path, "shapeChanges"), "GeosInThisNotInThat", "CURRENT")
                    else:
                        arcpy.CreateFileGDB_management("{}\\{}".format( \
                            path, "shapeChanges"), "GeosInThisNotInThat", "CURRENT")
                else:
                    os.mkdir("{}\\{}".format(path, "shapeChanges"))
                    arcpy.CreateFileGDB_management("{}\\{}".format( \
                        path, "shapeChanges"), "GeosInThisNotInThat", "CURRENT")

                if arcpy.Exists("{}\\{}".format(path, "attrChanges")):
                    if arcpy.Exists("{}\\{}\\{}.gdb".format( \
                            path, "attrChanges", "AttrsInThisNotInThat")):
                        arcpy.Delete_management("{}\\{}\\{}.gdb".format( \
                            path, "attrChanges", "AttrsInThisNotInThat"))
                        arcpy.CreateFileGDB_management("{}\\{}".format( \
                            path, "attrChanges"), "AttrsInThisNotInThat", "CURRENT")
                    else:
                        arcpy.CreateFileGDB_management("{}\\{}".format( \
                            path, "attrChanges"), "AttrsInThisNotInThat", "CURRENT")
                else:
                    os.mkdir("{}\\{}".format(path, "attrChanges"))
                    arcpy.CreateFileGDB_management("{}\\{}".format( \
                        path, "attrChanges"), "AttrsInThisNotInThat", "CURRENT")
            return

        def CopyIdenticalShapes(fc, baseLyr, outFolderPath, basefc):
            layerfileName = "{}\\{}.lyr".format( \
                env.scratchFolder, fc)
            arcpy.SaveToLayerFile_management( \
                baseLyr, layerfileName)
            baseGDB = "{}\\attrChanges\\AttrsInThisNotInThat.gdb" \
                .format(outFolderPath)
            arcpy.Copy_management(basefc, "{}\\{}".format(baseGDB, fc))
            with da.UpdateCursor("{}\\{}".format(baseGDB, fc), "*") as cursor:
                for row in cursor:
                    cursor.deleteRow()

            cursor = da.InsertCursor("{}\\{}".format(baseGDB, fc), "*")
            with da.SearchCursor(layerfileName, "*") as _cursor:
                for row in _cursor:
                    cursor.insertRow(row)

            del cursor
            arcpy.Delete_management(layerfileName)

            return

        def CopyUnidenticalShapes(fc, base_lyr, outFolderPath, basefc):
            layerfile_name = "{}\\{}.lyr".format(env.scratchFolder, fc)
            arcpy.SaveToLayerFile_management(base_lyr, layerfile_name)
            baseGDB = "{}\\attrChanges\\GeosInThisNotInThat.gdb".format(outFolderPath)
            arcpy.Copy_management(basefc, "{}\\{}".format(baseGDB, fc))
            with da.UpdateCursor("{}\\{}".format(baseGDB, fc), "*") as cursor:
                for row in cursor:
                    cursor.deleteRow()
            cursor = da.InsertCursor("{}\\{}".format(baseGDB, fc), "*")
            with da.SearchCursor(layerfile_name, "*") as _cursor:
                for row in _cursor:
                    cursor.insertRow(row)
            arcpy.Delete_management(layerfile_name)

            return

        def myCheckGeometries(fclist):
            result = arcpy.CheckGeometry_management(fclist, "ClientGeoCheck").getOutput(0)
            count = int(arcpy.GetCount_management(result).getOutput(0))
            if count:
                arcpy.Copy_management(result, "{}\\{}".format(env.scratchGDB, "ClientGeoCheck"))

                arcpy.AddError("""Geometry Errors found in the Client Geodatabase.\n
                Error tables has been exported to the scratch Geodatabase""")
                print("""Geometry Errors found in the Client Geodatabase.\n
                Error tables has been exported to the scratch Geodatabase""")
            else:
                pass

            del result
            del count
            return

        def MatchFields(basefc, compfc):
            fields = arcpy.ListFields(basefc)
            basefieldnames = [f.name for f in fields]

            compfields = arcpy.ListFields(compfc)
            compfieldnames = [f.name for f in compfields]

            infields = []
            infields.extend([f for f in basefieldnames if f in compfieldnames])

            for f in ["OBJECTID", "Shape"]:
                if f in infields:
                    infields.remove(f)

            infields.append("Shape")

            arcpy.AddMessage("These are the compare fields :: {}".format(infields))
            print("These are the infields :: {}".format(infields))

            return infields

        def myListFeatureClasses(gdb, store):
            env.workspace = gdb
            obj = store
            dlist = arcpy.ListDatasets()
            if len(dlist) > 0:
                for d in dlist:
                    flist = arcpy.ListFeatureClasses("", "", d)
                    for f in flist:
                        obj[f.upper()] = "{}\\{}\\{}".format(gdb, d, f)

            flist = arcpy.ListFeatureClasses()
            if len(flist) > 0:
                for f in flist:
                    obj[f.upper()] = arcpy.Describe(f).catalogPath
            return obj

        def CompareFeatureShapes(idfcList, baseObj, compObj):
            for fc in idfcList:
                basefc = baseObj[fc]
                compfc = compObj[fc]
                i = 0
                with da.SearchCursor(basefc, "*") as cursor:
                    for row in cursor:
                        i += 1
                precount = i
                if precount > 0:
                    arcpy.AddMessage("{} features exist in {}".format( \
                        precount, fc))
                    print("{} features exist in {}".format( \
                        precount, fc))
                    baseLyr = "in_memory\\{}_baseLyr".format(fc)
                    compLyr = "in_memory\\{}_compLyr".format(fc)

                    for x in [baseLyr, compLyr]:
                        if arcpy.Exists(x):
                            arcpy.Delete_management(x)
                            print("{} has been deleted".format(x))

                    arcpy.MakeFeatureLayer_management(basefc, baseLyr)
                    arcpy.MakeFeatureLayer_management(compfc, compLyr)
                    arcpy.SelectLayerByLocation_management( \
                        baseLyr, "ARE_IDENTICAL_TO", compLyr, "", "NEW_SELECTION")

                    # Isolate the features with identical geometry and export
                    postcount = int(arcpy.GetCount_management(baseLyr). \
                                    getOutput(0))
                    if postcount != 0:
                        CopyIdenticalShapes(fc, baseLyr, outFolderPath, basefc)
                        for x in [baseLyr, compLyr]:
                            if arcpy.Exists(x):
                                arcpy.Delete_management(x)
                                print("{} has been deleted".format(x))

                        compFile = "{}\\{}temp".format(env.scratchGDB, fc)
                        if arcpy.Exists(compFile):
                            arcpy.Delete_management(compFile)

                        sr = arcpy.SpatialReference(basefc)
                        arcpy.CreateFeatureclass_management(env.scratchGDB, "{}temp" % fc, \
                                                            template=basefc, has_m="SAME_AS_TEMPLATE", \
                                                            has_z="SAME_AS_TEMPLATE", \
                                                            spatial_reference=sr)
                        cursor = da.InsertCursor(compFile, "*")
                        with da.SearchCursor(compfc, "*") as _cursor:
                            for row in _cursor:
                                cursor.insertRow(row)
                        del cursor

                        arcpy.MakeFeatureLayer_management(basefc, baseLyr)
                        arcpy.MakeFeatureLayer_management(compFile, compLyr)
                        arcpy.SelectLayerByLocation_management( \
                            compLyr, "ARE_IDENTICAL_TO", baseLyr, "", "NEW_SELECTION")
                        saveLayer = "{}\\{}.lyr".format(env.scratchFolder, fc)
                        if arcpy.Exists(saveLayer):
                            arcpy.Delete_management(saveLayer)
                        arcpy.SaveToLayerFile_management(compLyr, saveLayer)

                        CompareAttributes(basefc, saveLayer)
                    else:
                        feedback(1, """None of the  features from the
                                         baseFc {} are identical to the compfc""".format(fc))

                    for x in [baseLyr, compLyr]:
                        if arcpy.Exists(x):
                            arcpy.Delete_management(x)

                    # Isolate the features with geometry that is not identical
                    arcpy.MakeFeatureLayer_management(basefc, baseLyr)
                    arcpy.MakeFeatureLayer_management(compfc, compLyr)
                    arcpy.SelectLayerByLocation_management( \
                        baseLyr, "ARE_IDENTICAL_TO", compLyr, "", "NEW_SELECTION")
                    arcpy.SelectLayerByAttribute_management( \
                        baseLyr, "SWITCH_SELECTION")
                    postcount = int(arcpy.GetCount_management(baseLyr). \
                                    getOutput(0))
                    if postcount != 0:
                        arcpy.AddMessage("""{} features for {} are not\n
                        identical in shape""".format(postcount, fc))
                        CopyUnidenticalShapes(fc, baseLyr, outFolderPath, basefc)
                        ## TODO,,, Add these fcs to the map if available as layers
                    else:
                        feedback(1, """All features from the baseFc {}are
                        identical to the compfc""".format(fc))

                else:
                    # arcpy.AddMessage("No features exist in {}".format(fc))
                    pass

        def CompareAttributes(basefc, compFile):

            x, y = [basefc, compFile]
            name = arcpy.Describe(fc[0]).baseName.upper()

            infields = MatchFields(x, y)

            compshapes = {}
            try:

                with da.SearchCursor(compFile, infields) as cursor:
                    for row in cursor:
                        if row[-1] not in compshapes.keys():
                            compshapes[row[-1]] = []
                            compshapes[row[-1]].append(row[:-1])
                        else:
                            compshapes[row[-1]].append(row[:-1])

                compKeys = compshapes.viewkeys()
                with da.UpdateCursor(basefc, infields) as cursor:
                    for row in cursor:
                        if row[-1] in compKeys:
                            fcs = compshapes[row[-1]]
                            if len(fcs) > 1:
                                flag = True
                                for i in range(len(fcs)):
                                    while flag == True:
                                        if row[:-1] != fcs[i]:
                                            flag = False
                                if flag == True:
                                    cursor.deleteRow()
                                    compshapes.pop(fcs)
                            else:
                                if row[:-1] == fcs:
                                    cursor.deleteRow()
                                    compshapes.pop(fcs)
                            del fcs
                        else:
                            pass
                del compKeys


            except Exception as e:
                feedback(2, ("{} :: {}".format(
                    e.message, arcpy.getMessages())))

            arcpy.Delete_management(compFile)

            return
            #### Begin the execution here by Creating File Structure

        try:
            CreateFileStructure(outfolder)
        except Exception as e:
            feedback(2, "{} :: {}".format(e.message, arcpy.GetMessages()))

        arorafcs = []
        clientfcs = []

        for obj in [{base_gdb: arorafcs}, {test_gdb: clientfcs}]:
            ingdb = obj.keys()[0]
            outlist = obj[ingdb]
            env.workspace = ingdb
            datasets = arcpy.ListDatasets()
            for d in datasets:
                env.workspace = os.path.join(ingdb, d)
                fcs = arcpy.ListFeatureClasses()
                outlist.extend([arcpy.Describe(fc).catalogPath for fc in fcs])
            env.workspace = ingdb
            fcs = arcpy.ListFeatureClasses()
            for fc in fcs:
                outlist.extend([arcpy.Describe(fc).catalogPath for fc in fcs])

            # Run the esri FindIdentical tool on all the features classes in the outlist
            if len(outlist):
                for fc in outlist:
                    try:
                        arcpy.FindIdentical_management(fc, "{}\\{}".format(env.scratchGDB, \
                                                                           arcpy.Describe(fc).baseName), \
                                                       "Shape")
                    except Exception as e:
                        feedback(3, "{} :: {}".format(e.message, arcpy.GetMessages()))

        ### We now have all of the feature classes for each geodatabase
        package = {base_gdb: arorafcs, test_gdb: clientfcs}
        keys = [k for k, v in package.iteritems()]
        feedback(0, ("These are the two input Geodatabases {}".format(keys)))

        ## This model is run twice, the baseGDB will switch the second time
        for key in keys:
            try:
                baseList = []
                compList = []
                ######################
                outFolderPath = ""  ####
                ######################
                compGDBpath = ""  ####
                ######################

                if key == base_gdb:
                    baseList.extend(package[key])
                    compList.extend(package[test_gdb])
                    outFolderPath = masterfolder_path
                    # this gdb will be used to compare the attributes from the temporary gdb that gets created
                    compGDBpath = AroraMasterGDB
                elif key == test_gdb:
                    baseList.extend(package[key])
                    compList.extend(package[base_gdb])
                    outFolderPath = clientfolder_path
                    # this gdb will be used to compare the attributes from the temporary gdb that gets created
                    compGDBpath = base_gdb

                # compare the baseList to the compList
                baseList.sort()
                compList.sort()

                # perform geometry checks on both of the feature class lists
                for list in [baseList, compList]:
                    try:
                        myCheckGeometries(list)
                    except Exception as e:
                        feedback(1, "{} :: {}".format(e.message, arcpy.GetMessages()))

                baseObj = {}
                for fc in baseList:
                    name = fc.split("\\")[-1].upper()
                    baseObj[name] = fc

                compObj = {}
                for fc in compList:
                    name = fc.split("\\")[-1].upper()
                    compObj[name] = fc

                baseKeys = baseObj.keys()
                compKeys = compObj.keys()

                extrafcinbase = [fc for fc in baseKeys if fc not in compKeys]
                feedback(1, "These feature classes are in the baseList but not in the compList, they will be\
                exported to the GeosInThisNotInThat.gdb :: {}".format(extrafcinbase))

                if len(extrafcinbase):
                    for fc in extrafcinbase:
                        target = "{}\\attrChanges\\GeosInThisNotInThat.gdb".format(outFolderPath)
                        arcpy.Copy_management(baseObj[fc], "{}\\{}".format(target, fc))

                idfcList = [fc for fc in baseKeys if fc in compKeys]
                feedback(1, "These are the feature classes that will be compared across \
                geodatabases :: {}".format(idfcList))

                ## For each feature in baseKeys compare exactly to compKeys
                for name in idfcList:
                    try:
                        try:
                            os.remove("{}\\{}.txt".format(env.scratchFolder, name))
                        except:
                            pass

                        basefc = baseObj[name]
                        targetfc = compObj[name]
                        result = arcpy.FeatureCompare_management(basefc, targetfc, "OBJECTID", "ALL",
                                                                 out_compare_file="{}\\{}.txt".format(env.scratchFolder,
                                                                                                      name)).getOutput(1)
                        print result
                        if result == "false":
                            feedback(1, """There are differences between {0} in the GDBs. \n
                                        Comparison result for {0} has been exported to the scratch folder \n
                                    located at {1}""".format(name, env.scratchFolder))

                            CompareFeatureShapes(idfcList, baseObj, compObj)

                        elif result == "true":
                            feedback(1, "{} match successfull".format(name))
                            try:
                                os.remove("{}\\{}.txt".format(env.scratchFolder, name))
                            except:
                                feedback(1, "Unable to remove match export text file from scratch folder")
                    except Exception as e:
                        feedback(1, "{} :: {}".format(e.message, arcpy.GetMessages()))

            except Exception as e:
                feedback(1, "{} :: {}".format(e.message, arcpy.GetMessages()))

