'''
    MacroScanner - scan Foldit all.macro file and generate Lua 
 
    Copyright (C) 2020 LociOiling

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.

    Details:

    Process each recipe in a Foldit all.macro file.

    Generate Lua for each GUI recipe.

    This version ignores the existing Lua recipes.
    
    all.macro uses "JSON Spirit" format, which is just slightly 
    different than standard JSON, at least in the Foldit version.
    In Foldit, there are no commas between keyword-value pairs.
    We'll solve that using "railroad methods", involving hammers, 
    crowbars, and blowtorches. Maybe shoulda writa a parser?
 
    version 1.0 - LociOiling - 20201208
    version 1.1 - LociOiling - 202012xx
        + added LuaV1 and LuaV2 options to allow dumping Lua recipes
        + added noGUI option to allow skipping GUI recipes
        + added outdir option to allow specifying where Lua files go
        + added new SelectBands and SelectSegment for user picks
        + correct LWS user picks "by stride"
        + correct LWS missing iterations 
        + correct LWS segment selection logic for user picks
        + handle old GUI example recipes with missing attributes
        + handle multiline comments in GUI recipes
        + handle missing number of iterations for GUI example 1
        + streamline some of the common error conditions
        + handle single.macro format
'''

import argparse
import sys
import os
import json
import re


#
#   JSONize - convert JSON-spirit to JSON
#
#   JSON-spirit as seen in Foldit is 
#   lacking commas between the K-V pairs.
#
#   JSONize restores the commas in an
#   unsubtle brute-force fashion that is so
#   totally un-Pythonic it could be FORTRAN.
#
#   JSONize coughs up an exception if can't 
#   cope with its input.
#
#   motto: we're gonna needa bigger hammer!
#
#   arguments:
#   
#   spirit - string containing the spirit-formatted pairs
#
#   returns:
#
#   Python dictionary containing K-V pairs
#   The values in the dictionary may in turn 
#   need to be JSONized.
#
def JSONize ( spirit ):
    rlines = spirit.splitlines ()
    scount = len ( rlines )
    rout = ""
    lout = 0
    for rll in rlines:
        lout = lout + 1
        if  not rll.find ( "{" ) == 0 \
        and not rll.find ( "}" ) == 0:
            if lout < scount - 1:
                rout = rout + rll + ",\n" # add a comma
            else:
                rout = rout + rll         # no comma on last one
    rout = "{\n" + rout + "\n}\n"         # we know it can do that
    rxx = json.loads ( rout )
    return rxx

def ListLua ( rxx, outdir ):
#
#   process entire recipe
#
    def get_valid_filename(s):  # borrowed from Django
        s = str(s).strip().replace(' ', '_')
        return re.sub(r'(?u)[^-\w.]', '', s)
    rxxfile = get_valid_filename ( rxx [ "name" ] ) + ".lua" 
    with open ( os.path.join ( outdir, rxxfile ), "w" ) as fout:
    #
    #   print the recipe attributes as a Lua block comment
    #   (slightly different list than the one for a GUI recipe)
    #
        rxattrs = [
             "name",
             "desc",
             "type",
             "folder_name", 
             "hidden",
             "mid",
             "mrid",
             "parent",
             "parent_mrid",
             "player_id",
             "share_scope",
             "uses",
             "script_version",
             "ver"
             ]
        fout.write ( "--[[\n\n" )
        for attr in rxattrs:
            fout.write ( "    {} = {}\n".format ( attr, rxx [ attr ] ) )
        fout.write ( "\n]]--\n" )
        #for thing in rxx:
        #    print ( thing )
        try:    
            line = rxx [ "script" ]
            fout.write ( "{}\n".format ( line ) )
        except:
            pass
    return

#
#   ListCmds - list the commands in a GUI recipe
#
#   arguments:
#   
#   rxx    - JSON object containing recipe
#   detail - include dump of GUI values as comments if true
#   outdir - output directory
#
#   note: lots of helper functions first - 
#         the action starts far down below,
#         just before "def main" 
#
def ListCmds ( rxx, detail, outdir ):
#   
#   railroad methods on full display in these generator routines
#
    def doSegPick ( ref ):
        refi = int ( ref ) 

    #
    #   segref is the Lua table containing a list of segments
    #
        segref = "segList_"
        segref = segref + ref

    #   
    #   if the referenced user pick doesn't exist, create it
    #   using dialog.SelectSegments
    #
        if refi > len ( segpick ):
            segpick.append ( segref )
            fout.write ( "    {} = dialog.SelectSegments ()\n".format ( segref ) )
        return segref

    def doBndPick ( ref ):
        refi = int ( ref ) 

    #
    #   bndref is the Lua table containing a list of segments
    #
        bndref = "bndList_"
        bndref = bndref + ref

    #   
    #   if the referenced user pick doesn't exist, create it
    #   using dialog.SelectBands
    #
        if refi > len ( bndpick ):
            bndpick.append ( bndref )
            fout.write ( "    {} = dialog.SelectBands ()\n".format ( bndref ) )
        return bndref

    def safeVal ( rxx, top, key, missing ):
    #
    #   handle a missing ingredient -- 
    #   mainly to allow processing old 
    #   GUI example recipes
    #
        val = missing
        try:
            val = rxx [ top ] [ key ]
        except:
            pass
        return val

    def safeIters ( rxx ):
        val = safeVal ( rxx, "num_of_iterations", "val", "-1" ) 
        if val == "-1":
            fout.write ( "--  TODO: set missing iterations\n" )
        if val == "0":
            fout.write ( "--  TODO: set iterations for \"until stopped\"\n" )
        return val
    
    def safeStart ( rxx, resnam ):
        start = safeVal ( rxx, resnam, "startval", "-1" ) 
        if start == "-1":
            fout.write ( "--  TODO: starting index for \"by stride\" not specified\n" )
            fout.write ( "--  TODO: incomplete {} ingredient\n".format ( resnam ) )
        return start
    def safeIncr ( rxx, resnam ):
        incr = safeVal ( rxx, resnam, "stepval", "-1" ) 
        if incr == "-1":
            fout.write ( "--  TODO: increment for \"by stride\" not specified\n" )
            fout.write ( "--  TODO: incomplete {} ingredient\n".format ( resnam ) )
        return incr

    def missingRes ( funcname, value ):
        fout.write ( "--  TODO: undefined residues ingredient\n" )
        sval = str ( value )
        if len ( sval ) > 0:
            fout.write ( "--  TODO: select segments for {} ( {} )\n".format ( funcname, sval ) )
        else:
            fout.write ( "--  TODO: select segments for {} ()\n".format ( funcname ) )
        return

    def genShake ( args ):
        val = safeIters ( args )
        fout.write ( "    structure.ShakeSidechainsAll ( {} )\n".format ( val ) )
        return
    def genWiggle ( args ):
        val = safeIters ( args )
        fout.write ( "    structure.WiggleAll ( {} )\n".format ( val ) )        
        return

    def genLocalWiggle ( args ):
        def genAll ():
            val = safeIters ( args )
            fout.write ( "    structure.LocalWiggleAll ( {} )\n".format ( val ) )
            return
        def genByStride ():
            val = safeIters ( args )
            if args [ "residues" ] [ "startnam" ] == "single_residue_by_index":
                start = safeStart ( args, "residues" )
                incr = safeIncr ( args, "residues" )
                fout.write ( "    for seg = {}, structure.GetCount (), {} do\n".format ( start, incr ) )
                fout.write ( "        selection.DeselectAll ()\n" )
                fout.write ( "    --  TODO: use selection.SelectRange to local wiggle multiple segments\n" )
                fout.write ( "        selection.Select ( seg )\n" )
                fout.write ( "        structure.LocalWiggleSelected ( {} )\n".format ( val ) )
                fout.write ( "    end\n" )
            if args [ "residues" ] [ "startnam" ] == "residues_ref":
                segref = doSegPick (  args [ "residues" ] [ "startval" ] )
                fout.write ( "    for seg = 1, #{} do\n".format ( segref ) )
                fout.write ( "        selection.DeselectAll ()\n" )
                fout.write ( "    --  TODO: use selection.SelectRange to local wiggle multiple segments\n" )
                fout.write ( "        selection.Select ( {} [ seg ] )\n".format ( segref ) )
                fout.write ( "        structure.LocalWiggleSelected ( {} )\n".format ( val ) )
                fout.write ( "    end\n" )
            return
        def genReference ():
            val = safeIters ( args )
            segref = doSegPick (  args [ "residues" ] [ "ref" ] )
            fout.write ( "    for seg = 1, #{} do\n".format ( segref ) )
            fout.write ( "        selection.DeselectAll ()\n" )
            fout.write ( "    --  TODO: use selection.SelectRange to local wiggle multiple segments\n" )
            fout.write ( "        selection.Select ( {} [ seg ] )\n".format ( segref ) )
            fout.write ( "        structure.LocalWiggleSelected ( {},  true, true )\n".format ( val ) ) 
            fout.write ( "    end\n" )
            return
        def genUndefined ():
            val = safeIters ( args )
            missingRes ( "structure.LocalWiggleSelected", val )
            fout.write ( "    structure.LocalWiggleSelected ( {} )\n".format ( val ) )
            return
        restyps = {
            "residues_all":         genAll,
            "residues_by_stride":   genByStride,
            "residues_ref":         genReference, 
            "residues_undefined":   genUndefined,
            }
        typ = args [ "residues" ] [ "name" ] 
        restyps [ typ ] ()
        return

    def genFreeze ( args ):
        def genAll ():
            fout.write ( "    freeze.FreezeAll ()\n" )
            return
        def genByStride ():
            if args [ "residues" ] [ "startnam" ] == "single_residue_by_index":
                start = safeStart ( args, "residues" )
                incr = safeIncr ( args, "residues" )
                fout.write ( "    for seg = {}, structure.GetCount (), {} do\n".format ( start, incr ) )
                fout.write ( "        freeze.Freeze ( seg, true, true )\n" )
                fout.write ( "    end\n" )
            if args [ "residues" ] [ "startnam" ] == "residues_ref":
                segref = doSegPick (  args [ "residues" ] [ "startval" ] )
                fout.write ( "    for seg = 1, #{} do\n".format ( segref ) )
                fout.write ( "        freeze.Freeze ( {} [ seg ], true, true )\n".format ( segref ) ) 
                fout.write ( "    end\n" )
            return
        def genReference ():
            segref = doSegPick (  args [ "residues" ] [ "ref" ] )
            fout.write ( "    for seg = 1, #{} do\n".format ( segref ) )
            fout.write ( "        freeze.Freeze ( {} [ seg ], true, true )\n".format ( segref ) ) 
            fout.write ( "    end\n" )
            return
        def genUndefined ():
            missingRes ( "freeze.Freeze", "" )
            fout.write ( "    freeze.Freeze ()\n" )
            return
        restyps = {
            "residues_all":         genAll,
            "residues_by_stride":   genByStride,
            "residues_ref":         genReference, 
            "residues_undefined":   genUndefined,
            }
        typ = args [ "residues" ] [ "name" ] 
        restyps [ typ ] ()
        return

    def genUnfreeze ( args ):
        def genAll ():
            fout.write ( "    freeze.UnfreezeAll ()\n" )
            return
        def genByStride ():
            if args [ "residues" ] [ "startnam" ] == "single_residue_by_index":
                start = safeStart ( args, "residues" )
                incr = safeIncr ( args, "residues" )
                fout.write ( "    for seg = {}, structure.GetCount (), {} do\n".format ( start, incr ) )
                fout.write ( "        freeze.Unfreeze ( seg, true, true )\n" )
                fout.write ( "    end\n" )
            if args [ "residues" ] [ "startnam" ] == "residues_ref":
                segref = doSegPick (  args [ "residues" ] [ "startval" ] )
                fout.write ( "    for seg = 1, #{} do\n".format ( segref ) )
                fout.write ( "        freeze.Unfreeze ( {} [ seg ], true, true )\n".format ( segref ) ) 
                fout.write ( "    end\n" )
            return
        def genReference ():
            segref = doSegPick (  args [ "residues" ] [ "ref" ] )
            fout.write ( "    for seg = 1, #{} do\n".format ( segref ) )
            fout.write ( "        freeze.Unfreeze ( {} [ seg ], true, true )\n".format ( segref ) ) 
            fout.write ( "    end\n" )
            return
        def genUndefined ():
            missingRes ( "freeze.Unfreeze", "" )
            fout.write ( "    freeze.Unfreeze ()\n" )
            return        
        restyps = {
            "residues_all":         genAll,
            "residues_by_stride":   genByStride,
            "residues_ref":         genReference, 
            "residues_undefined":   genUndefined,
            }
        typ = args [ "residues" ] [ "name" ] 
        restyps [ typ ] ()
        return
    def genSetSS ( args ):
        sscodes = ( "H", "L", "E" )
        def decodeSS ():
            ss = args [ "structure" ] [ "val" ]
            if ss != "-1":
                ss = sscodes [ int ( ss ) ]
            else:
                fout.write ( "--  TODO: undefined secondary structure ingredient\n" )
            return ss
        def genAll ():
            ss = decodeSS ()
            fout.write ( "    selection.SelectAll ()\n" )
            fout.write ( "    structure.SetSecondaryStructureSelected ( \"{}\" )\n".format ( ss ) )
            fout.write ( "    selection.DeselectAll ()\n" )
            return
        def genByStride ():
            ss = decodeSS ()
            if args [ "residues" ] [ "startnam" ] == "single_residue_by_index":
                start = safeStart ( args, "residues" )
                incr = safeIncr ( args, "residues" )
                fout.write ( "    selection.DeselectAll ()\n" )
                fout.write ( "    for seg = {}, structure.GetCount (), {} do\n".format ( start, incr ) ) 
                fout.write ( "       selection.Select ( seg )\n")
                fout.write ( "    end\n" )
                fout.write ( "    structure.SetSecondaryStructureSelected ( \"{}\" )\n".format ( ss ) )
                fout.write ( "    selection.DeselectAll ()\n" )
            if args [ "residues" ] [ "startnam" ] == "residues_ref":
                segref = doSegPick (  args [ "residues" ] [ "startval" ] )
                fout.write ( "    selection.DeselectAll ()\n" )
                fout.write ( "    for seg = 1, #{} do\n".format ( segref ) )
                fout.write ( "        selection.Select ( {} [ seg ] )\n".format ( segref ) ) 
                fout.write ( "    end\n" )
                fout.write ( "    structure.SetSecondaryStructureSelected ( \"{}\" )\n".format ( ss ) )
                fout.write ( "    selection.DeselectAll ()\n" )
            return
        def genReference ():
            ss = decodeSS ()
            segref = doSegPick (  args [ "residues" ] [ "ref" ] )
            fout.write ( "    selection.DeselectAll ()\n" )
            fout.write ( "    for seg = 1, #{} do\n".format ( segref ) )
            fout.write ( "        selection.Select ( {} [ seg ]  )\n".format ( segref ) ) 
            fout.write ( "    end\n" )
            fout.write ( "    structure.SetSecondaryStructureSelected ( \"{}\" )\n".format ( ss ) )
            fout.write ( "    selection.DeselectAll ()\n" )
            return
        def genUndefined ():
            ss = decodeSS ()
            missingRes ( "structure.SetSecondaryStructureSelected", ss )
            fout.write ( "    structure.SetSecondaryStructureSelected ( \"{}\" )\n".format ( ss ) )
            return
        restyps = {
            "residues_all":         genAll,
            "residues_by_stride":   genByStride,
            "residues_ref":         genReference, 
            "residues_undefined":   genUndefined,
            }
        typ = args [ "residues" ] [ "name" ] 
        restyps [ typ ] ()
        return
    def genSetAA ( args ):
        def decodeAA ():
            aa = args [ "aa" ] [ "val" ]
            if aa == "-1":
                fout.write ( "--  TODO: undefined amino acid ingredient\n" )
            return aa
        def genAll ():
            aa = decodeAA ()
            fout.write ( "    selection.SelectAll ()\n" )
            fout.write ( "    structure.structure.SetAminoAcidSelected ( \"{}\" )\n".format ( aa ) )
            fout.write ( "    selection.DeselectAll ()\n" )
            return
        def genByStride ():
            aa = decodeAA ()
            if args [ "residues" ] [ "startnam" ] == "single_residue_by_index":
                start = safeStart ( args, "residues" )
                incr = safeIncr ( args, "residues" )
                fout.write ( "    selection.DeselectAll ()\n" )
                fout.write ( "    for seg = {}, structure.GetCount (), {} do\n".format ( start, incr ) )
                fout.write ( "       selection.Select ( seg )\n" )
                fout.write ( "    end\n" )
                fout.write ( "    structure.SetAminoAcidSelected ( \"{}\" )\n".format ( aa ) )
                fout.write ( "    selection.DeselectAll ()\n" )
            if args [ "residues" ] [ "startnam" ] == "residues_ref":
                segref = doSegPick (  args [ "residues" ] [ "startval" ] )
                fout.write ( "    selection.DeselectAll ()\n" )
                fout.write ( "    for seg = 1, #{} do\n".format ( segref ) )
                fout.write ( "        selection.Select ( {} [ seg ] )\n".format ( segref ) ) 
                fout.write ( "    end\n" )
                fout.write ( "    structure.SetAminoAcidSelected ( \"{}\" )\n".format ( aa ) )
                fout.write ( "    selection.DeselectAll ()\n" )
            return
        def genReference ():
            aa = decodeAA ()
            segref = doSegPick (  args [ "residues" ] [ "ref" ] )
            fout.write ( "    selection.DeselectAll ()\n" )
            fout.write ( "    for seg = 1, #{} do\n".format ( segref ) )
            fout.write ( "        selection.Select ( {} [ seg ]  )\n".format ( segref ) ) 
            fout.write ( "    end\n" )
            fout.write ( "    structure.SetAminoAcidSelected ( \"{}\" )\n".format ( aa ) )
            fout.write ( "    selection.DeselectAll ()\n" )
            return
        def genUndefined ():
            aa = decodeAA ()
            missingRes ( "structure.SetAminoAcidSelected", aa )
            fout.write ( "    structure.SetAminoAcidSelected ( \"{}\" )\n".format ( aa ) )
            return
        restyps = {
            "residues_all":         genAll,
            "residues_by_stride":   genByStride,
            "residues_ref":         genReference, 
            "residues_undefined":   genUndefined,
            }
        typ = args [ "residues" ] [ "name" ] 
        restyps [ typ ] ()
        return
    def genMutate ( args ):
        def genAll ():
            iters = safeIters ( args )
            fout.write ( "    structure.MutateSidechainsAll ( {} )\n".format ( iters ) )
            return
        def genByStride ():
            iters = safeIters ( args )
            if args [ "residues" ] [ "startnam" ] == "single_residue_by_index":
                start = safeStart ( args, "residues" )
                incr = safeIncr ( args, "residues" )
                fout.write ( "    selection.DeselectAll ()\n" )
                fout.write ( "    for seg = {}, structure.GetCount (), {} do\n".format ( start, incr ) ) 
                fout.write ( "       selection.Select ( seg )\n")
                fout.write ( "    end\n" )
                fout.write ( "    structure.MutateSidechainsSelected  ( \"{}\" )\n".format ( iters ) )
                fout.write ( "    selection.DeselectAll ()\n" )
            if args [ "residues" ] [ "startnam" ] == "residues_ref":
                segref = doSegPick (  args [ "residues" ] [ "startval" ] )
                fout.write ( "    selection.DeselectAll ()\n" )
                fout.write ( "    for seg = 1, #{} do\n".format ( segref ) )
                fout.write ( "        selection.Select ( {} [ seg ] )\n".format ( segref ) ) 
                fout.write ( "    end\n" )
                fout.write ( "    structure.MutateSidechainsSelected  ( \"{}\" )\n".format ( iters ) )
                fout.write ( "    selection.DeselectAll ()\n" )
            return
        def genReference ():
            iters = safeIters ( args )
            segref = doSegPick (  args [ "residues" ] [ "ref" ] )
            fout.write ( "    selection.DeselectAll ()\n" )
            fout.write ( "    for seg = 1, #{} do\n".format ( segref ) )
            fout.write ( "        selection.Select ( {} [ seg ]  )\n".format ( segref ) ) 
            fout.write ( "    end\n" )
            fout.write ( "    structure.MutateSidechainsSelected  ( \"{}\" )\n".format ( iters ) )
            fout.write ( "    selection.DeselectAll ()\n" )
            return
        def genUndefined ():
            iters = safeIters ( args )
            missingRes ( "structure.MutateSidechainsSelected", iters )
            fout.write ( "    structure.MutateSidechainsSelected  ( \"{}\" )\n".format ( iters ) )
            return
        restyps = {
            "residues_all":         genAll,
            "residues_by_stride":   genByStride,
            "residues_ref":         genReference, 
            "residues_undefined":   genUndefined,
            }
        typ = args [ "residues" ] [ "name" ] 
        restyps [ typ ] ()
        return
#  ===================================================================================================================
#  genAddBands expands to 4 x 4 = 16 routines
#  ===================================================================================================================
    def genAddBands ( args ):
        def genAllAll ():
            fout.write ( "    for seg1 = 1, structure.GetCount () do\n"  )
            fout.write ( "        for seg2 = seg1  + 1, structure.GetCount () do\n" )
            fout.write ( "            band.AddBetweenSegments ( seg1, seg2 )\n" )
            fout.write ( "        end\n" )
            fout.write ( "    end\n" )
            return
        def genAllByStride ():
            if args [ "residues2" ] [ "startnam" ] == "single_residue_by_index":
                start = safeStart ( args, "residues2" )
                incr = safeIncr ( args, "residues2" )
                fout.write ( "    for seg1 = 1, structure.GetCount () do\n"  )
                fout.write ( "        for seg2 = {}, structure.GetCount (), {} do\n".format ( start, incr ) )
                fout.write ( "            if seg1 ~= seg2 then\n" )
                fout.write ( "                band.AddBetweenSegments ( seg1, seg2 )\n" )
                fout.write ( "            end\n" )
                fout.write ( "        end\n" )
                fout.write ( "    end\n" )
            if args [ "residues2" ] [ "startnam" ] == "residues_ref":
                segref = doSegPick (  args [ "residues2" ] [ "startval" ] )
                fout.write ( "    for seg1 = 1, structure.GetCount () do\n"  )
                fout.write ( "        for segidx2 = 1, #{} do\n".format ( segref ) )
                fout.write ( "            if seg1 ~= seg2 then\n" )
                fout.write ( "                band.AddBetweenSegments ( seg1,  {} [ segidx2 ] )\n".format ( segref ) ) 
                fout.write ( "            end\n" )
                fout.write ( "        end\n" )
                fout.write ( "    end\n" )
            return
        def genAllReference ():
            segref = doSegPick (  args [ "residues2" ] [ "ref" ] )
            fout.write ( "    for seg1 = 1, structure.GetCount () do\n"  )
            fout.write ( "        for segidx2 = 1, #{} do\n".format ( segref ) )
            fout.write ( "            if seg1 ~= {} [ segidx2 ] then\n".format ( segref ) )
            fout.write ( "                band.AddBetweenSegments ( seg1, {} [ segidx2 ] )\n".format ( segref ) )
            fout.write ( "            end\n" )
            fout.write ( "        end\n" )
            fout.write ( "    end\n" )
            return
        def genAllUndefined ():
            fout.write ( "--  TODO: undefined residues2 ingredient\n" )
            fout.write ( "--  TODO: select segments for segmentIndex2 argument to band.AddBetweenSegments\n" )
            fout.write ( "    for seg1 = 1, structure.GetCount () do\n"  )
            fout.write ( "        band.AddBetweenSegments ( seg1, )\n" )
            fout.write ( "    end\n" )
            return
        def genByStrideAll ():
            if args [ "residues1" ] [ "startnam" ] == "single_residue_by_index":
                start = safeStart ( args, "residues1" )
                incr = safeIncr ( args, "residues1" )
                fout.write ( "    for seg1 = {}, structure.GetCount (), {} do\n".format ( start, incr ) )
                fout.write ( "        for seg2 = seg1 + 1, structure.GetCount () do\n"  )
                fout.write ( "            if seg1 ~= seg2 then\n" )
                fout.write ( "                band.AddBetweenSegments ( seg1, seg2 )\n" )
                fout.write ( "            end\n" )
                fout.write ( "        end\n" )
                fout.write ( "    end\n" )
            if args [ "residues1" ] [ "startnam" ] == "residues_ref":
                segref = doSegPick (  args [ "residues1" ] [ "startval" ] )
                fout.write ( "    for segidx1 = 1, #{} do\n".format ( segref ) )
                fout.write ( "        for seg2 = 1, structure.GetCount () do\n" )
                fout.write ( "            if {} [ segidx1 ] ~= seg2 then\n".format ( segref ) )
                fout.write ( "                band.AddBetweenSegments ( {} [ segidx1 ], seg2 )\n".format ( segref ) )
                fout.write ( "            end\n" )
                fout.write ( "        end\n")
                fout.write ( "    end\n" )
            return
    #
    #  lot of branches on the main line of this railroad
    #
        def genByStrideByStride ():
            if args [ "residues1" ] [ "startnam" ] == "single_residue_by_index":
                start1 = safeStart ( args, "residues1" )
                incr1 = safeIncr ( args, "residues1" )
                if args [ "residues2" ] [ "startnam" ] == "single_residue_by_index":
                    start2 = safeStart ( args, "residues2" )
                    incr2 = safeIncr ( args, "residues2" )
                    fout.write ( "    for seg1 = {}, structure.GetCount (), {} do\n".format ( start1, incr1 ) )
                    fout.write ( "        for seg2 = {}, structure.GetCount (), {} do\n".format ( start2, incr2 ) )
                    fout.write ( "            if seg1 ~= seg2 then\n" )
                    fout.write ( "                band.AddBetweenSegments ( seg1, seg2 )\n" )
                    fout.write ( "            end\n" )
                    fout.write ( "        end\n" )
                    fout.write ( "    end\n" )
                if args [ "residues2" ] [ "startnam" ] == "residues_ref":
                    segref2 = doSegPick (  args [ "residues2" ] [ "startval" ] )
                    fout.write ( "    for seg1 = {}, structure.GetCount (), {} do\n".format ( start1, incr1 ) )
                    fout.write ( "       for segidx2 = 1, #{} do\n".format ( segref2 ) )
                    fout.write ( "            if seg1 ~= {} [ segidx2 ] then\n".format ( segref2 ) )
                    fout.write ( "                band.AddBetweenSegments ( seg1, {} [ segidx2 ] )\n".format ( segref2 ) )
                    fout.write ( "            end\n" )
                    fout.write ( "        end\n")
                    fout.write ( "    end\n" )
            if args [ "residues1" ] [ "startnam" ] == "residues_ref":
                segref1 = doSegPick (  args [ "residues1" ] [ "startval" ] )
                if args [ "residues2" ] [ "startnam" ] == "single_residue_by_index":
                    start2 = safeStart ( args, "residues2" )
                    incr2 = safeIncr ( args, "residues2" )
                    fout.write ( "    for segidx1 = 1, #{} do\n".format ( segref1 ) )
                    fout.write ( "        for seg2 = {}, structure.GetCount (), {} do\n".format ( start2, incr2 ) )
                    fout.write ( "            if seg1 ~= seg2 then\n" )
                    fout.write ( "                band.AddBetweenSegments ( {} [ segidx1 ], seg2 )\n".format ( segref1 ) )
                    fout.write ( "            end\n" )
                    fout.write ( "        end\n" )
                    fout.write ( "    end\n" )
                if args [ "residues2" ] [ "startnam" ] == "residues_ref":
                    segref2 = doSegPick (  args [ "residues2" ] [ "startval" ] )
                    fout.write ( "--  TODO: generating for loop using \"{}\" as reference\n".format ( segref2 ) )
                    fout.write ( "--  TODO: for loop syntax is valid, but \"{}\" is undefined\n".format ( segref2 ) )
                    fout.write ( "    for segidx1 = 1, #{} do\n".format ( segref1 ) )
                    fout.write ( "       for segidx2 = 1, #{} do\n".format ( segref2 ) )
                    fout.write ( "            if {} [ segidx1 ] ~= {} [ segidx2 ] then\n".format ( segref1, segref2 ) )
                    fout.write ( "                band.AddBetweenSegments ( {} [ segidx1 ], {} [ segidx2 ] )\n".format ( segref1, segref2 ) )
                    fout.write ( "            end\n" )
                    fout.write ( "        end\n")
                    fout.write ( "    end\n" )
            return
        def genByStrideReference ():
            if args [ "residues1" ] [ "startnam" ] == "single_residue_by_index":
                start = safeStart ( args, "residues1" )
                incr = safeIncr ( args, "residues1" )
                segref2 = doSegPick (  args [ "residues2" ] [ "ref" ] )
                fout.write ( "    for seg1 = {}, structure.GetCount (), {} do\n".format ( start, incr ) )
                fout.write ( "        for segidx2 = 1, #{} do\n".format ( segref2 ) )
                fout.write ( "            if seg1 ~= {} [ segidx2 ] then\n".format ( segref2 ) )
                fout.write ( "                band.AddBetweenSegments ( seg1, {} [ segidx2 ] )\n".format ( segref2 ) )
                fout.write ( "            end\n" )
                fout.write ( "        end\n" )
                fout.write ( "    end\n" )
            if args [ "residues1" ] [ "startnam" ] == "residues_ref":
                segref1 = doSegPick (  args [ "residues1" ] [ "startval" ] )
                segref2 = doSegPick (  args [ "residues2" ] [ "ref" ] )
                fout.write ( "    for segidx1 = 1, #{} do\n".format ( segref1 ) )
                fout.write ( "        for segidx2 = 1, #{} do\n".format ( segref2 ) )
                fout.write ( "            if {} [ segidx1 ] ~= {} [ segidx2 ] then\n".format ( segref1, segref2 ) )
                fout.write ( "                band.AddBetweenSegments ( {} [ segidx1 ],  {} [ segidx2 ] )\n".format ( segref1, segref2 ) ) 
                fout.write ( "            end\n" )
                fout.write ( "        end\n" )
                fout.write ( "    end\n" )
            return
        def genByStrideUndefined ():
            fout.write ( "--  TODO: undefined residues2 ingredient\n" )
            fout.write ( "--  TODO: select segments for segmentIndex2 argument to band.AddBetweenSegments\n" )

            if args [ "residues1" ] [ "startnam" ] == "single_residue_by_index":
                start = safeStart ( args, "residues1" )
                incr = safeIncr ( args, "residues1" )
                fout.write ( "    for seg1 = {}, structure.GetCount (), {} do\n".format ( start, incr ) )
                fout.write ( "        band.AddBetweenSegments ( seg1, )\n" )
                fout.write ( "    end\n" )
            if args [ "residues1" ] [ "startnam" ] == "residues_ref":
                segref = doSegPick (  args [ "residues1" ] [ "startval" ] )
                fout.write ( "    for segidx1 = 1, #{} do\n".format ( segref ) )
                fout.write ( "        band.AddBetweenSegments ( {} [ segidx1 ], )\n".format ( segref ) )
                fout.write ( "    end\n" )
            return
        def genReferenceAll ():
            segref = doSegPick (  args [ "residues1" ] [ "ref" ] )
            fout.write ( "    for segidx1 = 1, #{} do\n".format ( segref ) )
            fout.write ( "        for seg2 = 1, structure.GetCount () do\n"  )
            fout.write ( "            if {} [ segidx1 ] ~= seg2 then\n".format ( segref ) )
            fout.write ( "                band.AddBetweenSegments ( {} [ segidx1 ], seg2 )\n".format ( segref ) )
            fout.write ( "            end\n" )
            fout.write ( "        end\n" )
            fout.write ( "    end\n" )
            return
        def genReferenceByStride ():
            segref1 = doSegPick (  args [ "residues1" ] [ "ref" ] )
            if args [ "residues2" ] [ "startnam" ] == "single_residue_by_index":
                start = safeStart ( args, "residues2" )
                incr = safeIncr ( args, "residues2" )
                fout.write ( "    for segidx1 = 1, #{} do\n".format ( segref1 ) )
                fout.write ( "        for seg2 = {}, structure.GetCount (), {} do\n".format ( start, incr ) )
                fout.write ( "            if {} [ segidx1 ] ~= seg2 then\n".format ( segref1 ) )
                fout.write ( "                band.AddBetweenSegments ( {} [ segidx1 ], seg2 )\n".format ( segref1 ) )
                fout.write ( "            end\n" )
                fout.write ( "        end\n" )
                fout.write ( "    end\n" )
            if args [ "residues2" ] [ "startnam" ] == "residues_ref":
                segref2 = doSegPick (  args [ "residues2" ] [ "ref" ] )
                fout.write ( "    for segidx1 = 1, #{} do\n".format ( segref1 ) )
                fout.write ( "        for segidx2 = 1, #{} do\n".format ( segref2 ) )
                fout.write ( "            if {} [ segidx1 ] ~= {} [ segidx2 ] then\n" )
                fout.write ( "                band.AddBetweenSegments ( {} [ segidx1 ], {} [ segidx2 ] )\n".format ( segref1, segref2 ) ) 
                fout.write ( "            end\n" )
                fout.write ( "        end\n" )
                fout.write ( "    end\n" )
            return
        def genReferenceReference ():
            segref1 = doSegPick (  args [ "residues1" ] [ "ref" ] )
            segref2 = doSegPick (  args [ "residues2" ] [ "ref" ] )
            fout.write ( "--  TODO: generating for loop using \"{}\" as reference\n".format ( segref2 ) )
            fout.write ( "--  TODO: for loop syntax is valid, but \"{}\" is undefined\n".format ( segref2 ) )

            fout.write ( "    for segidx1 = 1, #{} do\n".format ( segref1 ) )
            fout.write ( "        for segidx2 = 1, #{} do\n".format ( segref2 ) )
            fout.write ( "            if {} [ segidx1 ] ~= {} [ segidx2 ] then\n".format ( segref1, segref2 ) )
            fout.write ( "                band.AddBetweenSegments ( {} [ segidx1 ], {} [ segidx2 ] )\n".format ( segref1, segref2 ) )
            fout.write ( "            end\n" )
            fout.write ( "        end\n" )
            fout.write ( "    end\n" )
            return
        def genReferenceUndefined ():
            segref = doSegPick (  args [ "residues1" ] [ "ref" ] )
            fout.write ( "--  TODO: undefined residues2 ingredient\n" )
            fout.write ( "--  TODO: select segments for segmentIndex2 argument to band.AddBetweenSegments\n" )
            fout.write ( "    for segidx1 = 1, #{} do\n".format ( segref ) )
            fout.write ( "        band.AddBetweenSegments ( {} [ segidx1 ], )\n".format ( segref ) )
            return
        def genUndefinedAll ():
            fout.write ( "--  TODO: undefined residues1 ingredient\n" )
            fout.write ( "--  TODO: select segments for segmentIndex1 argument to band.AddBetweenSegments\n" )
            fout.write ( "    for seg2 = 1, structure.GetCount () do\n" )
            fout.write ( "        band.AddBetweenSegments ( , seg2 )\n" )
            fout.write ( "    end\n" )
            return
        def genUndefinedByStride ():
            fout.write ( "--  TODO: undefined residues1 ingredient\n" )
            fout.write ( "--  TODO: select segments for segmentIndex1 argument to band.AddBetweenSegments\n" )
            if args [ "residues2" ] [ "startnam" ] == "single_residue_by_index":
                start = safeStart ( args, "residues2" )
                incr = safeIncr ( args, "residues2" )
                fout.write ( "    for seg2 = {}, structure.GetCount (), {} do\n".format ( start, incr ) )
                fout.write ( "        if seg1 ~= seg2 then\n" )
                fout.write ( "            band.AddBetweenSegments ( , seg2 )\n" )
                fout.write ( "        end\n" )
                fout.write ( "    end\n" )
            if args [ "residues2" ] [ "startnam" ] == "residues_ref":
                segref = doSegPick (  args [ "residues2" ] [ "startval" ] )
                fout.write ( "    for segidx2 = 1, #{} do\n".format ( segref ) )
                fout.write ( "        band.AddBetweenSegments ( ,  {} [ segidx2 ] )\n".format ( segref ) ) 
                fout.write ( "    end\n" )
            return
        def genUndefinedReference ():
            fout.write ( "--  TODO: undefined residues1 ingredient\n" )
            fout.write ( "--  TODO: select segments for segmentIndex1 argument to band.AddBetweenSegments\n" )
            segref = doSegPick (  args [ "residues2" ] [ "ref" ] )
            fout.write ( "    for segidx2 = 1, #{} do\n".format ( segref ) )
            fout.write ( "        band.AddBetweenSegments ( , {} [ segidx2 ] )\n".format ( segref ) )
            fout.write ( "    end\n" )
            return
        def genUndefinedUndefined ():
            fout.write ( "--  TODO: undefined residues1 ingredient\n" )
            fout.write ( "--  TODO: select segments for segmentIndex1 argument to band.AddBetweenSegments\n" )
            fout.write ( "--  TODO: undefined residues2 ingredient\n" )
            fout.write ( "--  TODO: select segments for segmentIndex2 argument to band.AddBetweenSegments\n" )
            fout.write ( "    band.AddBetweenSegments ()\n" )
            return
    #   ============================
    #   16 candles there on the wall
    #   ============================
        restyps = {
            "residues_all_residues_all":                genAllAll,
            "residues_all_residues_by_stride":          genAllByStride,
            "residues_all_residues_ref":                genAllReference,
            "residues_all_residues_undefined":          genAllUndefined,
            "residues_by_stride_residues_all":          genByStrideAll,
            "residues_by_stride_residues_by_stride":    genByStrideByStride,
            "residues_by_stride_residues_ref":          genByStrideReference,
            "residues_by_stride_residues_undefined":    genByStrideUndefined,
            "residues_ref_residues_all":                genReferenceAll, 
            "residues_ref_residues_by_stride":          genReferenceByStride, 
            "residues_ref_residues_ref":                genReferenceReference, 
            "residues_ref_residues_undefined":          genReferenceUndefined, 
            "residues_ref_residues_all":                genReferenceAll, 
            "residues_ref_residues_by_stride":          genReferenceByStride, 
            "residues_ref_residues_ref":                genReferenceReference, 
            "residues_ref_residues_undefined":          genReferenceUndefined, 
            "residues_undefined_residues_all":          genUndefinedAll,
            "residues_undefined_residues_by_stride":    genUndefinedByStride,
            "residues_undefined_residues_ref":          genUndefinedReference,
            "residues_undefined_residues_undefined":    genUndefinedUndefined,
            }
        typ1 = args [ "residues1" ] [ "name" ] 
        typ2 = args [ "residues2" ] [ "name" ] 
        ttyp = typ1 + "_" + typ2
        restyps [ ttyp ] ()
        return
    def genDisable ( args ):
        def genAll ():
            fout.write ( "    band.DisableAll ()\n" )
            return
        def genConnected ():
            fout.write ( "--  TODO: the \"connected\" option actually selected spacebands...\n" )
            fout.write ( "--  TODO: the for loop below selects spacebands in the same way\n" )
            fout.write ( "    for bnd = 1, band.GetCount () do\n" )
            fout.write ( "        if band.GetResidueEnd ( bnd ) == 0 then\n" )
            fout.write ( "            band.Disable ( bnd )\n" )
            fout.write ( "        end\n" )
            fout.write ( "    end\n" )
            return
        def genReference ():
            bndref = doBndPick ( args [ "bands" ] [ "ref" ] )
            fout.write ( "    for bnd = 1, #{} do\n".format ( bndref ) )
            fout.write ( "        band.Disable ( {} [ bnd ] )\n".format ( bndref ) )
            fout.write ( "    end\n" )
            return
        def genUndefined ():
            fout.write ( "--  TODO: undefined bands ingredient\n" )
            fout.write ( "--  TODO: select bands for band.Disable\n" )
            fout.write ( "    band.Disable ()\n" )
            return
        bndtyps = {
            "bands_all":        genAll,
            "bands_connected":  genConnected,
            "bands_reference":  genReference, 
            "bands_undefined":  genUndefined,
            }
        typ = args [ "bands" ] [ "name" ] 
        bndtyps [ typ ] ()
        return
    def genEnable ( args ):
        def genAll ():
            fout.write ( "    band.EnableAll ()\n" )
            return
        def genConnected ():
            fout.write ( "--  TODO: the \"connected\" option actually selected spacebands...\n" )
            fout.write ( "--  TODO: the for loop below selects spacebands in the same way\n" )
            fout.write ( "    for bnd = 1, band.GetCount () do\n" )
            fout.write ( "        if band.GetResidueEnd ( bnd ) == 0 then\n" )
            fout.write ( "            band.Enable ( bnd )\n" )
            fout.write ( "        end\n" )
            fout.write ( "    end\n" )
            return
        def genReference ():
            bndref = doBndPick ( args [ "bands" ] [ "ref" ] )
            fout.write ( "    for bnd = 1, #{} do\n".format ( bndref ) )
            fout.write ( "        band.Enable ( {} [ bnd ] )\n".format ( bndref ) )
            fout.write ( "    end\n" )
            return
        def genUndefined ():
            fout.write ( "--  TODO: undefined bands ingredient\n" )
            fout.write ( "--  TODO: select bands for band.Enable\n" )
            fout.write ( "    band.Enable ()\n" )
            return
        bndtyps = {
            "bands_all":        genAll,
            "bands_connected":  genConnected,
            "bands_reference":  genReference, 
            "bands_undefined":  genUndefined,
            }
        typ = args [ "bands" ] [ "name" ] 
        bndtyps [ typ ] ()
        return
    def genRemove ( args ):
        def genAll ():
            fout.write ( "    band.DeleteAll ()\n" )
            return
        def genConnected ():
            fout.write ( "--  TODO: the \"connected\" option actually selected spacebands...\n" )
            fout.write ( "--  TODO: the for loop below selects spacebands in the same way\n" )
            fout.write ( "    for bnd = 1, band.GetCount () do\n" )
            fout.write ( "        if band.GetResidueEnd ( bnd ) == 0 then\n" )
            fout.write ( "            band.Delete ( bnd )\n" )
            fout.write ( "        end\n" )
            fout.write ( "    end\n" )
            return
        def genReference ():
            bndref = doBndPick ( args [ "bands" ] [ "ref" ] )
            fout.write ( "    for bnd = 1, #{} do\n".format ( bndref ) )
            fout.write ( "        band.Delete ( {} [ bnd ] )\n".format ( bndref ) )
            fout.write ( "    end\n" )
            return
        def genUndefined ():
            fout.write ( "--  TODO: undefined bands ingredient\n" )
            fout.write ( "--  TODO: select bands for band.Delete\n" )
            fout.write ( "    band.Delete ()\n" )
            return
        bndtyps = {
            "bands_all":        genAll,
            "bands_connected":  genConnected,
            "bands_reference":  genReference, 
            "bands_undefined":  genUndefined,
            }
        typ = args [ "bands" ] [ "name" ] 
        bndtyps [ typ ] ()
        return
    def genSetStrength ( args ):
        def genAll ():
            bndstr = args [ "strength" ] [ "val" ]
            if bndstr == "-1":
                fout.write ( "--  TODO: missing strength ingredient\n" )
            fout.write ( "    for bnd = 1, band.GetCount () do\n" )
            fout.write ( "        band.SetStrength ( bnd, {} )\n".format ( bndstr ) )
            fout.write ( "    end\n" )
            return
        def genConnected ():
            bndstr = args [ "strength" ] [ "val" ]
            if bndstr == "-1":
                fout.write ( "--  TODO: missing strength ingredient\n" )
            fout.write ( "--  TODO: the \"connected\" option actually selected spacebands...\n" )
            fout.write ( "--  TODO: the for loop below selects spacebands in the same way\n" )
            fout.write ( "    for bnd = 1, band.GetCount () do\n" )
            fout.write ( "        if band.GetResidueEnd ( bnd ) == 0 then\n" )
            fout.write ( "            band.SetStrength ( bnd, {} )\n".format ( bndstr ) )
            fout.write ( "        end\n" )
            fout.write ( "    end\n" )
            return
        def genReference ():
            bndstr = args [ "strength" ] [ "val" ]
            if bndstr == "-1":
                fout.write ( "--  TODO: missing strength ingredient\n" )
            bndref = doBndPick ( args [ "bands" ] [ "ref" ] )
            fout.write ( "    for bnd = 1, #{} do\n".format ( bndref ) )
            fout.write ( "        band.SetStrength ( {} [ bnd ], {} )\n".format ( bndref, bndstr ) )
            fout.write ( "    end\n" )
            return
        def genUndefined ():
            bndstr = args [ "strength" ] [ "val" ]
            if bndstr == "-1":
                fout.write ( "--  TODO: missing strength ingredient\n" )
            fout.write ( "--  TODO: undefined bands ingredient\n" )
            fout.write ( "--  TODO: select bands for band.SetStrength ( {} )\n".format ( bndstr )  )
            fout.write ( "    band.SetStrength ()\n" )
            return
        bndtyps = {
            "bands_all":        genAll,
            "bands_connected":  genConnected,
            "bands_reference":  genReference, 
            "bands_undefined":  genUndefined,
            }
        typ = args [ "bands" ] [ "name" ] 
        bndtyps [ typ ] ()        
        return
    def genSetCI ( args ):
        val = args [ "importance" ] [ "val" ]
        if val == "-1":
            fout.write ( "--  TODO: missing importance ingredient\n" )
        fout.write ( "    behavior.SetClashingImportance ( {} )\n".format ( val ) )
        return
    def genResetPuzzle ( args ):
        fout.write ( "    puzzle.StartOver ()\n" )
        return
    def genRestoreAbs ( args ):
        fout.write ( "    absolutebest.Restore ()\n" )
        return
    def genSetRecent ( args ):
        fout.write ( "    recentbest.Save ()\n" )
        return
    def genRestoreRecent ( args ):
        fout.write ( "    recentbest.Restore ()\n" )
        return
    def genQuicksave ( args ):
        val = args [ "slot" ] [ "val" ]
        if val == "-1":
            fout.write ( "--  TODO: missing slot ingredient\n" )
        fout.write ( "    save.Quicksave ( {} )\n".format ( val ) )
        return
    def genQuickload ( args ):
        val = args [ "slot" ] [ "val" ]
        if val == "-1":
            fout.write ( "--  TODO: missing slot ingredient\n" )
        fout.write ( "    save.Quickload ( {} )\n".format ( val ) )
        return
    def genComment ( args ):
        val = args [ "comment" ] [ "val" ]
        lines = val.splitlines ()
        fout.write ( "--\n" )
        for line in lines:
            fout.write ( "--  {}\n".format ( line ) )
        fout.write ( "--\n" )
        return
#
#   rxcmds list functions to generate the Lua for each command
#   (the third column names the arguments, but doesn't get used)
#   some commands have "Action" names, like "ActionNoviceResetRecentBest",
#   where "Standalone" is used in recent versions of Foldit
#
    rxcmds = { 
        "shake":                               ( genShake,           [ "num_of_iterations" ] ),
        "wiggle":                              ( genWiggle,          [ "num_of_iterations" ] ), 
        "local_wiggle":                        ( genLocalWiggle,     [ "num_of_iterations", "residues" ] ),
        "lock":                                ( genFreeze,          [ "residues" ] ),
        "unlock":                              ( genUnfreeze,        [ "residues" ] ),
        "set_secondary_structure":             ( genSetSS,           [ "residues", "structure" ] ),
        "set_amino_acid":                      ( genSetAA,           [ "residues", "aa" ] ),
        "mutate":                              ( genMutate,          [ "num_of_iterations", "residues" ] ), 
        "add_bands":                           ( genAddBands,        [ "residues1", "residues2" ] ),
        "disable":                             ( genDisable,         [ "bands" ] ),
        "enable":                              ( genEnable,          [ "bands" ] ),
        "remove":                              ( genRemove,          [ "bands" ] ),
        "set_strength":                        ( genSetStrength,     [ "bands", "strength" ] ),
        "behavior":                            ( genSetCI,           [ "importance" ] ),
        "ActionStandaloneResetPuzzle":         ( genResetPuzzle,     [] ),
        "ActionStandaloneRestoreAbsoluteBest": ( genRestoreAbs,      [] ),
        "ActionNoviceRestoreAbsoluteBest":     ( genRestoreAbs,      [] ),
        "ActionStandaloneResetRecentBest":     ( genSetRecent,       [] ),
        "ActionNoviceResetRecentBest":         ( genSetRecent,       [] ),
        "ActionStandaloneRestoreRecentBest":   ( genRestoreRecent,   [] ),
        "ActionNoviceRestoreRecentBest":       ( genRestoreRecent,   [] ),
        "ActionStandaloneQuicksave":           ( genQuicksave,       [] ),
        "ActionNoviceQuicksave":               ( genQuicksave,       [] ),
        "ActionStandaloneQuickload":           ( genQuickload,       [] ),
        "ActionNoviceQuickload":               ( genQuickload,       [] ),
        "comment":                             ( genComment,         [ "comment" ] ),
        }

#
#   complex residues ingredient
#
    def getResidues ( arg, rxx ):
        def getAll ( rxx ):
            return {}
        def getByStride ( rxx ):
            startxx = JSONize ( rxx [ "start" ] )
            startnam = startxx [ "name" ]
            startval = "-1"
            if startnam == "single_residue_by_index":
                indexxx = JSONize ( startxx [ "index" ] )
                if indexxx [ "is_defined" ] == "1":
                    startval = indexxx [ "value" ]
            if startnam == "residues_ref":
                startval = startxx [ "ref-id" ]
            stepxx = JSONize ( rxx [ "step" ] )
            stepval = "-1"
            if stepxx [ "is_defined" ] == "1":
                stepval = stepxx [ "value" ]

            return { "startnam": startnam, "startval": startval, "stepval": stepval } # really not *that* bad
        def getReference ( rxx ):
            val = rxx [ "ref-id" ]
            return { "ref": val }
        def getUndefined ( rxx ):
            return {}
        names = {
            "residues_all":         [ "all",        getAll ],
            "residues_by_stride":   [ "by_stride",  getByStride ],
            "residues_ref":         [ "reference",  getReference ],
            "residues_undefined":   [ "undefined",  getUndefined ],
            }
        rnam = rxx [ "name" ]        
        rlst = { arg: { "name": rnam } }
        rlst [ arg ].update ( names [ rnam ] [ 1 ] ( rxx ) )
        return rlst
#
#   somewhat complex bands ingredient
#
    def getBands ( arg, rxx ):
        def getAll ( rxx ):
            return {}
        def getConnected ( rxx ):
            return {}
        def getReference ( rxx ):
            val = rxx [ "ref-id" ]
            return { "ref": val }
        def getUndefined ( rxx ):
            return {}
        names = {
            "bands_all":        [ "all",        getAll ],
            "bands_connected":  [ "connected",  getConnected ],
            "bands_reference":  [ "reference",  getReference ],
            "bands_undefined":  [ "undefined",  getUndefined ],
            }
        rnam = rxx [ "name" ]        
        rlst = { arg: { "name": rnam } }
        rlst [ arg ].update ( names [ rnam ] [ 1 ] ( rxx ) )
        return rlst
#
#   simple ingredients, just one value each
#
    def getIters ( arg, rxx ):
        val = ""
        if rxx [ "is_defined" ] == "1":
            val = rxx [ "value" ]
        else:
            val = "-1"
        return { arg: { "name": rxx [ "name" ], "val": val } }
    def getStructure ( arg, rxx ):
        if rxx [ "is_defined" ] == "1":
            val = rxx [ "value" ]
        else:
            val = "-1"
        return { arg: { "name": rxx [ "name" ], "val": val } }
    def getAA ( arg, rxx ):
        if rxx [ "is_defined" ] == "1":
            val = rxx [ "value" ]
        else:
            val = "-1"
        return { arg: { "name": rxx [ "name" ], "val": val } }
    def getStrength ( arg, rxx ):
        val = ""
        if rxx [ "is_defined" ] == "1":
            val = rxx [ "value" ]
        else:
            val = "-1"
        return { arg: { "name": rxx [ "name" ], "val": val } }
    def getImportance ( arg, rxx ):
        val = ""
        if rxx [ "is_defined" ] == "1":
            val = rxx [ "value" ]
        else:
            val = "-1"
        return { arg: { "name": rxx [ "name" ], "val": val } }
    def getSlot ( arg, rxx ):
        val = ""
        if rxx [ "is_defined" ] == "1":
            val = rxx [ "value" ]
        else:
            val = "-1"
        return { arg: { "name": rxx [ "name" ], "val": val } }
    def getComment ( arg, rxx ):
        val = ""
        if rxx [ "is_defined" ] == "1":
            val = rxx [ "value" ]
        else:
            val = "(TODO: add comment here)"
        return { arg: { "name": rxx [ "name" ], "val": val } }

#
#   rxargs tells which function to call for a given ingredient
#   
    rxargs = {
        "num_of_iterations":                    getIters,
        "residues":                             getResidues,
        "residues1":                            getResidues,
        "residues2":                            getResidues,
        "structure":                            getStructure,
        "aa":                                   getAA,
        "bands":                                getBands,
        "strength":                             getStrength,
        "importance":                           getImportance,
        "slot":                                 getSlot,
        "comment":                              getComment,
        }
#
#   process entire recipe
#
    def get_valid_filename(s):  # borrowed from Django
        s = str(s).strip().replace(' ', '_')
        return re.sub(r'(?u)[^-\w.]', '', s)
    rxxfile = get_valid_filename ( rxx [ "name" ] ) + ".lua" 
    with open ( os.path.join ( outdir, rxxfile ), "w" ) as fout:
    #
    #   print the recipe attributes as a Lua block comment
    #   (this list of attributes is specific to GUI recipes)
    #
        rxattrs = [
             "name",
             "desc",
             "size",
             "type",
             "folder_name", 
             "hidden",
             "mid",
             "mrid",
             "parent",
             "parent_mrid",
             "player_id",
             "share_scope",
             "uses"
             ]
        fout.write ( "--[[\n\n" )
        for attr in rxattrs:
            fout.write ( "    {} = {}\n".format ( attr, rxx [ attr ] ) )
        fout.write ( "\n]]--\n" )
    #
    #   track user picks for segments and bands
    #
        segpick = []
        bndpick = []
    #
    #   print each command 
    #
        cmdcnt = int ( rxx [ "size" ] )
        for cmdnum in range ( cmdcnt ):
            cmdnam = "action-{}".format ( cmdnum )
            cmdobj = JSONize ( rxx [ cmdnam ] )
            cmdcmd = cmdobj [ "name" ]
            cmdarg = ""
            for arg in cmdobj:
                if arg != "name":
                    if len ( cmdarg ) > 0:
                        cmdarg += ", "
                    cmdarg += arg

            if detail:
                fout.write ( "--  command {} = {} ({})\n".format ( cmdnum + 1, cmdcmd, cmdarg ) )
        #
        #   get the ingredients/arguments for the command
        #
            argl = {}
            for arg in cmdobj:
                if arg != "name":
                    argl.update ( rxargs [ arg ] ( arg, JSONize ( cmdobj [ arg ] ) ) )

            if detail:
                for axx in argl:
                    fout.write ( "--  {} = {}\n".format ( axx, argl [ axx ] ) )
                    
        #
        #   generate the Lua for the command
        #
            cmdgen = rxcmds [ cmdcmd ]
            cmdgen [ 0 ] ( argl )

    return
def checkAttrs ( rxx ):
#
#   check for the presence of each 
#   of the attributes, add a default
#   value if missing
#
#   this allows processing the old
#   GUI example recipes, which 
#   were missing certain attributes
#
#   this list includes the attributes
#   common to GUI and Lua recipes
#
    attrvals = {
         "name": "unknown",
         "desc": "unknown",
         "size": "0",
         "type": "gui",
         "folder_name": "unknown",  
         "hidden": "0",
         "mid": "0",
         "mrid": "0",
         "parent": "0",
         "parent_mrid": "0",
         "player_id": "0",
         "share_scope": "0",
         "uses": "0",
           }
    for attr in attrvals:
        try:
            safety = rxx [ attr ]
        except:
            rxx [ attr ] = attrvals [ attr ]
            pass
    return
def main ():
    ReVersion = "MacroScanner 1.1" 

    prog = 'python MacroScanner.py'
    description = ('Scan Foldit cookbook all.macro file for '
                   'GUI recipes and generate Lua equivalents.')
    parser = argparse.ArgumentParser(prog=prog, description=description)
    parser.add_argument('infile', nargs='?',
                        type=argparse.FileType(),
                        help='an all.macro file to be scanned',
                        default="all.macro")
    parser.add_argument('outfile', nargs='?',
                        type=argparse.FileType('w', encoding="utf-8"),
                        help='output file listing all recipes and their descriptions',
                        default=sys.stdout)
    parser.add_argument('--detail', action='store_true', default=False,
                        help='include details of each GUI command in Lua output')
    parser.add_argument('--LuaV1', action='store_true', default=False,
                        help='include recipes written using V1 of the Foldit Lua interface')
    parser.add_argument('--LuaV2', action='store_true', default=False,
                        help='include recipes written using V2 of the Foldit Lua interface')
    parser.add_argument('--noGUI', action='store_true', default=False,
                        help='don\'t include GUI recipes')
    parser.add_argument('--outdir', default=".",
                        help='output directory')

    options = parser.parse_args()

    recipes = 0
    guirecipes = 0
    guiskips = 0
    luarecipes = 0
    v1skips = 0
    v2skips = 0
    jsonerrors = 0

    linecnt = 0

    outdir = options.outdir
    if not os.path.exists(outdir):
        os.makedirs(outdir)

#
#   process the outer level, removing version and verify
#
#   the top level has a keyword-value pair for each recipe
#
    with options.infile as fp, options.outfile as fo:
        try:
            singlefmt = False
            singledict = {}
            fo.write ( ReVersion )
            fo.write ( "\n" )
            for line in fp:
                linecnt = linecnt + 1
                outpath = "line{0}.out".format ( linecnt )
                if  not line.find ( "version" ) == 0 \
                and not line.find ( "verify" ) == 0 \
                and not line.find ( "{" ) == 0 \
                and not line.find ( "}" ) == 0:
                    recipes = recipes + 1
                    #fo.write ( "line length = {}\n".format ( len ( line ) ) )
                    #fo.write ( "line slice = {}\n".format ( line [ 0:100 ] ) )
                    line = "{\n" + line + "}\n"
                    try:
                    #
                    #   the Foldit JSON Spirit escapes "," and "#", 
                    #   which is not standard
                    #   
                    #   we'll de-escape them here, with a regular 
                    #   expression which matches a variable number
                    #   of backslashes followed by  "," or "#"
                    #   
                    #   the backslashes are the first group, which is dropped
                    #   the  "," or "#" is the second group, the replacement
                    #
                        linex = re.sub ( r"(\\+)([#,])", r"\2", line )
                        rx = json.loads ( linex )
 
                    #
                    #   detect single.macro format in typical brute-force style
                    #
                        if not singlefmt:
                            for kk, vv in rx.items ():
                                if kk == "action-0":
                                    singlefmt = True
                                    fo.write ( "single.macro format\n")
                                    break
                    #
                    #   in single.macro format, accumulate each line into a dictionary
                    #
                        if singlefmt:
                            singledict.update ( rx )
                    #
                    #   in normal mode, the entire recipe is contained in the line we just read
                    #
                        else:
                            for kk, vv in rx.items ():
                            #
                            #   next level down has the content of each recipe
                            #
                                rxx = JSONize ( vv )
                                checkAttrs ( rxx )
                                fo.write ( "=========================================================================\n" )

                                fo.write ( "recipe = \"{}\", type = \"{}\"\n".format ( rxx [ "name" ], rxx [ "type"] ) )
                                fo.write ( "description = \"{}\"\n".format ( rxx [ "desc" ] ) )
                                if rxx [ "type" ] == "gui":
                                    guirecipes = guirecipes + 1
                                    if not options.noGUI:
                                        ListCmds ( rxx, options.detail, outdir )
                                    else:
                                        print ( "recipe skipped" )
                                        guiskips = guiskips + 1
                                if rxx [ "type" ] == "script":
                                    luarecipes = luarecipes + 1
                                    sver = rxx [ "script_version" ]
                                    if options.LuaV1 and sver == "1" or options.LuaV2 and sver == "2":
                                        ListLua ( rxx, outdir )
                                    else:
                                        print ( "recipe skipped" )
                                        if sver == "1":
                                            v1skips = v1skips + 1
                                        if sver == "2":
                                            v2skips = v2skips + 1

                    except json.JSONDecodeError as erred:
                        fo.write ( "JSON decode error: {}\n".format ( erred ) )
                        fo.write ( "error position {}\n".format ( erred.pos ) )
                        errchar = erred.doc [ erred.pos + 1 ]
                        fo.write ( "error character = \"{}\"\n".format ( errchar ) )
                        dlen = len ( erred.doc ) 
                        dstart = max ( 0, erred.pos - 10 )
                        dend = min ( dlen, erred.pos + 10 )
                        fo.write ( "error context = \"{}\" [ {}:{} ]\n".format ( erred.doc [ dstart: dend ], dstart, dend ) )
                        jsonerrors = jsonerrors + 1
                        pass
        #
        #   at the end, for single.macro format, dump the recipe
        #
            if singlefmt:
                checkAttrs ( singledict )
                fo.write ( "=========================================================================\n" )

                fo.write ( "recipe = \"{}\", type = \"{}\"\n".format ( singledict [ "name" ], singledict [ "type"] ) )
                fo.write ( "description = \"{}\"\n".format ( singledict [ "desc" ] ) )
                if singledict [ "type" ] == "gui":
                    guirecipes = guirecipes + 1
                    if not options.noGUI:
                        ListCmds ( singledict, options.detail, outdir )
                    else:
                        print ( "recipe skipped" )
                        guiskips = guiskips + 1
                if singledict [ "type" ] == "script":
                    luarecipes = luarecipes + 1
                    sver = singledict [ "script_version" ]
                    if options.LuaV1 and sver == "1" or options.LuaV2 and sver == "2":
                        ListLua ( singledict, outdir )
                    else:
                        print ( "recipe skipped" )
                        if sver == "1":
                            v1skips = v1skips + 1
                        if sver == "2":
                            v2skips = v2skips + 1

        except UnicodeDecodeError as erred:
            fo.write ( erred )
            fo.write ( "\n" )
            pass

        fo.write ( "=========================================================================\n" )
        fo.write ( ReVersion + " - complete\n" )
        fo.write ( "recipes read = {}\n".format ( recipes ) )
        fo.write ( "GUI recipes = {}\n".format ( guirecipes ) )
        if guiskips > 0:
            fo.write ( "GUI recipes skipped = {}\n".format ( guiskips ) )
        fo.write ( "Lua recipes = {}\n".format ( luarecipes ) )
        if v1skips > 0:
            fo.write ( "Lua V1 recipes skipped = {}\n".format ( v1skips ) )
        if v2skips > 0:
            fo.write ( "Lua V2 recipes skipped = {}\n".format ( v2skips ) )
        fo.write ( "JSON errors = {}\n".format ( jsonerrors ) )

if __name__ == "__main__":
   main ()
