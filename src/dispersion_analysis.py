import numpy as np
from scipy import stats
import matplotlib.pyplot as plt
from astropy.io import fits
from scipy.optimize import curve_fit
from regions import PixCoord, RectanglePixelRegion
plt.rcParams.update({'font.size': 16})

def calc_rel_angle_crossn(angle1, angle2):
    """
    Method of dealing with the wrapping issue in MDCF
    """
    angle1 = np.array(angle1)
    angle2 = np.array(angle2)
    n = len(angle1)
    if n == 1:
        x1 = (-1.0) * np.sin(angle1[0])
        y1 = np.cos(angle1[0])
        x2 = (-1.0) * np.sin(angle2[0])
        y2 = np.cos(angle2[0])
        v1 = np.array([x1, y1, 0])
        v2 = np.array([x2, y2, 0])
        C = np.cross(v1, v2)
        CdC = np.dot(C, C)
        vdgr = np.dot(v1, v2)
        d_ang0 = np.arctan2(np.sqrt(CdC), vdgr)
        return np.array([d_ang0])
    elif n > 1:
        x1 = (-1.0) * np.sin(angle1.reshape(1, n))
        y1 = np.cos(angle1.reshape(1, n))
        x2 = (-1.0) * np.sin(angle2.reshape(1, n))
        y2 = np.cos(angle2.reshape(1, n))
        v1 = np.array([x1, y1, np.zeros((1, n))])
        v2 = np.array([x2, y2, np.zeros((1, n))])
        vi = np.asmatrix(v1).T
        vf = np.asmatrix(v2).T
        try:
            C = np.cross(vi, vf)
        except:
            print("crossing error!")

        CdC = np.sum(C * C, 1)

        vdgr = []
        for i in range(len(vi)):
            vector = v1[0][0][i] * v2[0][0][i] + \
                        v1[1][0][i] * v2[1][0][i] + \
                        v1[2][0][i] * v2[2][0][i]
            vdgr.append(vector)
        vdgr = np.array(vdgr)
        d_ang0 = np.arctan2(np.sqrt(CdC), np.abs(vdgr)) 
        return d_ang0


def angular_dispersion_calculation(data, edge_length, beam_resolution, pixel_scale):
    """
    """
    x, y, pix_ang, dphi = [], [], [], []
    
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            if not np.isnan(data[i][j]):
                x.append(i)
                y.append(j)
                pix_ang.append(data[i][j])
    x = np.array(x)
    y = np.array(y)
    ang = np.array(pix_ang)

    nump = len(ang) 
    delta_r = []
    delta_phi = []
    phi = ang
  
    for i in range(nump):
        delta_x_arr = x[i] - x[(i+1):(nump)]
        delta_y_arr = y[i] - y[(i+1):(nump)]
        delta_r_arr = np.sqrt(delta_x_arr**2 + delta_y_arr**2)
        sz_phi = len(delta_x_arr)
        phi_ref = np.repeat(phi[i], sz_phi)

        if len(phi_ref) > 0:
            delta_phi_arr = calc_rel_angle_crossn(phi_ref, phi[(i+1):(nump)])

        delta_r.append(delta_r_arr)
        delta_phi.append(delta_phi_arr)

    delta_r = np.array(delta_r)
    delta_phi = np.array(delta_phi[:-1]) # Last value is added twice for some reason.

    delta_r = np.concatenate(delta_r).ravel() * pixel_scale # CONVERT THIS TO UNITS OF PARSEC
    delta_phi = np.concatenate(delta_phi).ravel()
    
    # User defines this but well go with Athena's for now.
    bin_edge = edge_length / pixel_scale
    
    print(bin_edge)
    
    if beam_resolution == 0:
        nbins = 21
    else:    
        print(edge_length)
        print(beam_resolution)
        nbins = np.floor((edge_length / beam_resolution * 5)) # Always want 5 samples / beam.
    
    print(f'Structure function analysis used: {nbins} number of bins')
    
    bin_edges = (np.linspace(0, bin_edge, int(nbins))) * pixel_scale 
    cos_disp, bin_edges_norm, bin_number_cos = stats.binned_statistic(delta_r, np.cos(delta_phi), 'mean', bins=bin_edges)
    cos_disp_sq, bin_edges_sq, bin_number_sq = stats.binned_statistic((delta_r)**2, np.cos(delta_phi), 'mean', bins=bin_edges**2)

    cos_disp = np.insert(cos_disp, 0, 1)
    cos_disp_sq = np.insert(cos_disp_sq, 0, 1)
        
    return [cos_disp, bin_edges_norm, cos_disp_sq, bin_edges_sq]
         
    
def data_cut(x_cen, y_cen, rad, image, show=False):
    '''
    Data cut to snip out a region from a map.
    '''
    if show:
        fig, ax = plt.subplots(figsize=(10,6))
        region = RectanglePixelRegion(center=PixCoord(x=x_cen, y=y_cen), width=rad, height=rad)
        plt.imshow(image, cmap='hsv')#, vmin=-np.pi/2, vmax=np.pi/2)
        plt.colorbar()
        region.plot(ax=ax, color='white')
        plt.show()
    reg = RectanglePixelRegion(center=PixCoord(x=x_cen, y=y_cen), width=rad, height=rad)
    mask = reg.to_mask()
    mask = reg.to_mask(mode='center')
    dt = mask.cutout(image)
    return dt
    

def Imshow(image, **kwargs):
    """
    Simple function display to an image.
    """
    plt.figure(figsize=(8, 6))
    plt.imshow(image, origin='lower')
    plt.colorbar()
    plt.show()

    
def linear_fit(x, m, b):
    """
    Linear Fit Function.
    """
    return m * x + b


def gauss_function(x, a, sigma):
    """
    Gaussian fit function.
    """
    return a * np.exp(-(x)**2 / (2 * sigma**2))


def total_gauss_function(x, a, W, delta):
    """
    Turbulent Gaussian fit function.
    """
    return a * np.exp(-(x)**2 / (2*(delta**2 + 2*W**2)))


def turbulent_cells(delta, cloud_dep, beam_res):
    """
    """
    return ((delta**2 + 2*(beam_res**2)) * cloud_dep) / (np.sqrt(2*np.pi) * delta**3)
