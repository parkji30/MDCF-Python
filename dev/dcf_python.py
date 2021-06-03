import numpy as np
import os
from scipy import stats
import matplotlib.pyplot as plt
from astropy.io import fits
from regions import PixCoord, CirclePixelRegion, RectanglePixelRegion


def Stokes_Polarization(Q, U):
    """
    Calcualtes the polarization of the angle using stokes Q and U maps.
    """
    return np.arctan2(Q, U)/2


def cos_disp_calculations(data, ds_scale):
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

    nump = len(ang) # -2
    w = 2.5 / 2.35 # arc seconds
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
    delta_phi = np.array(delta_phi[:-1])

    delta_r = np.concatenate(delta_r).ravel() * 10 / 512 * ds_scale # CONVERT THIS TO UNITS OF PARSEC
    delta_phi = np.concatenate(delta_phi).ravel()
    return delta_r, delta_phi


def multi_fit(delta_r, delta_phi, ttl, ds_scale, outer_distance, fit0=7, fitf=17, show=False):
    """

    """
    bin_range = (np.linspace(0, outer_distance, 21) + 0.5) * 10 / 512  * ds_scale

    # Binned Statistics calculation for the turbulent to ordered ratio.
    cos_disp, bin_edges_cos, bin_number_cos = stats.binned_statistic(delta_r, np.cos(delta_phi), 'mean', bins = bin_range)
    cos_disp_sq, bin_edges_sq, bin_number_sq = stats.binned_statistic(delta_r**2, np.cos(delta_phi), 'mean', bins = bin_range**2)
    cos_disp, bin_edges, bin_number_cos = stats.binned_statistic(delta_r, np.cos(delta_phi), 'mean', bins = bin_range)

    bin_edges_sq = np.insert(bin_edges_sq, 0, 0)
    cos_disp_sq = np.insert(cos_disp_sq, 0, 1)
    bin_edges = np.insert(bin_edges, 0, 0)
    cos_disp = np.insert(cos_disp, 0, 1)

    # Linear fit for the first two plots.
    popt_linear, _ = curve_fit(linear_fit,  bin_edges_sq[fit0:fitf], 1-cos_disp_sq[start:end])

    # Gaussian fit for the third plot.
    b2_l = linear_fit(bin_edges[:-1]**2, *popt_linear) - (1-cos_disp)

    # Gaussian Autocorrelation Function
    popt_gauss, __ = curve_fit(gauss_function, bin_edges[:-1], b2_l)

    print("Y-intercept: ", popt_linear[-1])
    print("Amplitude, sigma")
    print("Gaussian parameters are: ", popt_gauss)
    print("FWHM: ", popt_gauss[1] * 2.35)

    # Where we display the multi fit figures.
    fig = plt.figure(num=1, figsize =(12, 12))
    plt.subplot(3, 1, 1)
    plt.title(ttl)
    plt.plot(bin_edges_sq[:-1], 1-cos_disp_sq, linestyle ="none", marker="X", label="Data Points")
    plt.plot(bin_edges_sq, linear_fit(bin_edges_sq, *popt_linear), label='Linear Fit', linestyle="--")
    plt.ylabel("1 - Cosdisp")
    plt.xlabel("L $^2$ (Parsecs)", fontsize=11.5)
    plt.legend()
    plt.subplot(3, 1, 2)
    plt.plot(bin_edges[:-1], 1-cos_disp, linestyle ="none", marker="X", label="Data Points")
    plt.plot(bin_edges, linear_fit(bin_edges**2, *popt_linear), label='Linear Fit', linestyle="--")
    plt.ylabel("1 - Cosdisp")
    plt.xlabel("L (Parsecs)", fontsize=11.5)
    plt.legend()
    plt.subplot(3, 1, 3)
    plt.plot(bin_edges[:-1], gauss_function(bin_edges[:-1],*popt_gauss), label="Gaussian Fit", linestyle="--")
    plt.plot(bin_edges[:-1], b2_l, linestyle ="none", marker="X", label="Fit and Data Difference")
    plt.ylabel("b$^2$(l)")
    plt.xlabel("L (Parsecs)", fontsize=11.5)
    plt.legend()
    plt.show()


def data_cut(x_cen, y_cen, rad, data, show=False):
    """
    Cuts a circular region of data based on the map provided.
    """
    region = CirclePixelRegion(center=PixCoord(x=x_cen, y=y_cen), radius=rad)
    center = PixCoord(x_cen, y_cen)
    reg = CirclePixelRegion(center, rad)
    mask = reg.to_mask()
    mask = reg.to_mask(mode='center')
    dt = mask.cutout(data)

    if show:
        Imshow(dt)
    return dt