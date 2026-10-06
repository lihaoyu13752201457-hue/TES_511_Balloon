#!/usr/bin/env python3
"""Open the delivered WRL files with VTK and save an actual-reader preview."""
from pathlib import Path
import json, hashlib
import pyvista as pv
import vtk

P=Path(__file__).resolve().parents[1]
def main():
    results=[]
    for suffix in ('','_cutaway'):
        path=P/'figures'/f'Mass_model_AA{suffix}.wrl'
        plot=pv.Plotter(off_screen=True,window_size=(1600,1500))
        importer=vtk.vtkVRMLImporter();importer.SetFileName(str(path));importer.SetRenderWindow(plot.render_window);importer.Update()
        renderer=plot.render_window.GetRenderers().GetFirstRenderer()
        camera=renderer.GetActiveCamera();camera.SetPosition(90,-125,85);camera.SetFocalPoint(8,0,10);camera.SetViewUp(0,0,1);camera.ParallelProjectionOn()
        renderer.ResetCamera();renderer.ResetCameraClippingRange();renderer.SetBackground(1,1,1)
        plot.render_window.SetMultiSamples(4)
        # Use the actual imported scene, not a second mesh reconstruction.
        plot.render_window.Render()
        image=vtk.vtkWindowToImageFilter();image.SetInput(plot.render_window);image.SetInputBufferTypeToRGB();image.ReadFrontBufferOff();image.Update()
        png=P/'figures'/f'AA_3D{suffix}.png';writer=vtk.vtkPNGWriter();writer.SetFileName(str(png));writer.SetInputConnection(image.GetOutputPort());writer.Write()
        count=renderer.GetActors().GetNumberOfItems();assert count>2000,count
        results.append({'file':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'reader':'vtkVRMLImporter','actor_count':count,'preview':str(png)})
        plot.close()
    (P/'audit/wrl_reader_validation.json').write_text(json.dumps({'status':'PASS','files':results},indent=2)+'\n')
    print(json.dumps(results,indent=2))
if __name__=='__main__':main()
