def distribution_fit(data, distribution, discrete=False, xmin=None, xmax=None, find_xmin=False, find_xmax=False, comparison_alpha=None, force_positive_mean=False):
    """distribution_fit does things"""
    from numpy import log
    if xmin:
        xmin = float(xmin)
        data = data[data>=xmin]
    if xmax:
        xmax = float(xmax)
        data = data[data<=xmax]

    n = float(len(data))

    if distribution=='power_law' and not discrete and xmin and not xmax:
        from numpy import array, nan
        alpha = 1+n/\
                sum(log(data/xmin))
        loglikelihood = n*log(alpha-1.0) - n*log(xmin) - alpha*sum(log(data/xmin))
        if loglikelihood == nan:
            loglikelihood=0

        parameters = array([alpha])
        return parameters, loglikelihood
    
    else:
        if distribution=='power_law':
            initial_parameters=[1.5]
            likelihood_function = lambda parameters:\
                    power_law_likelihoods(\
                    data, parameters[0], xmin, xmax, discrete)

        elif distribution=='exponential':
            initial_parameters=[.5]
            likelihood_function = lambda parameters:\
                    exponential_likelihoods(\
                    data, parameters[0], xmin, xmax, discrete)

        elif distribution=='truncated_power_law':
            initial_parameters=[1.5, .5]
            likelihood_function = lambda parameters:\
                    truncated_power_law_likelihoods(\
                    data, parameters[0], parameters[1], xmin, xmax, discrete)

        elif distribution=='lognormal':
            from numpy import mean, std
            logdata = log(data)
            initial_parameters=[mean(logdata), std(logdata)]
            likelihood_function = lambda parameters:\
                    lognormal_likelihoods(\
                    data, parameters[0], parameters[1], xmin, xmax, discrete, force_positive_mean=force_positive_mean)

        from scipy.optimize import fmin
        parameters, negative_loglikelihood, iter, funcalls, warnflag, = \
                fmin(\
                lambda p: -sum(log(likelihood_function(p))),\
                initial_parameters, full_output=1, disp=False)
        loglikelihood =-negative_loglikelihood

    if not comparison_alpha:
        return parameters, loglikelihood

    pl_likelihoods = power_law_likelihoods(data, comparison_alpha, xmin, xmax, discrete)
    candidate_likelihoods = likelihood_function(parameters)
    R, p = loglikelihood_ratio(pl_likelihoods, candidate_likelihoods)
    return parameters, loglikelihood, R, p

def loglikelihood_ratio(likelihoods1, likelihoods2):
    from numpy import sqrt,log
    from scipy.special import erfc

    n = float(len(likelihoods1))

    loglikelihoods1 = log(likelihoods1)
    loglikelihoods2 = log(likelihoods2)

    R = sum(loglikelihoods1-loglikelihoods2)

    sigma = sqrt( \
    sum(\
    ( (loglikelihoods1-loglikelihoods2) - \
    (loglikelihoods1.mean()-loglikelihoods2.mean()) )**2 \
    )/n )

    p = erfc( abs(R) / (sqrt(2*n)*sigma) ) 
    return R, p

def find_xmin(data, discrete=False, xmax=None):
    from numpy import sort, unique, asarray, argmin, hstack, arange, sqrt
    if xmax:
        data = data[data<=xmax]
    noise_flag=False
#Much of the rest of this function was inspired by Adam Ginsburg's plfit code, specifically around lines 131-143 of this version: http://code.google.com/p/agpy/source/browse/trunk/plfit/plfit.py?spec=svn359&r=357  This code isn't exactly that code, though that code is MIT license. I don't know if that puts any requirements on this function.
    data = sort(data)
    xmins, xmin_indices = unique(data, return_index=True)

    alpha_MLE_function = lambda xmin: distribution_fit(data, 'power_law', xmin=xmin, xmax=xmax, discrete=discrete)
    fits  = asarray( map(alpha_MLE_function,xmins))
    alphas = hstack(fits[:,0])
    loglikelihoods = fits[:,1]

    ks_function = lambda index: power_law_ks_distance(data, alphas[index], xmins[index], xmax=xmax, discrete=discrete)
    Ds  = asarray( map(ks_function, arange(len(xmins))))

    sigmas = (alphas-1)/sqrt(len(data)-xmin_indices+1)
    good_values = sigmas<.1
    xmin_max = argmin(good_values)
    if xmin_max>0 and not good_values[-1]==True:
        Ds = Ds[:xmin_max]
        alphas = alphas[:xmin_max]
    else:
        noise_flag = True

    min_D_index = argmin(Ds)
    xmin = xmins[argmin(Ds)]
    D = Ds[min_D_index]
    alpha = alphas[min_D_index]
    loglikelihood = loglikelihoods[min_D_index]
    n = sum(data>=xmin)

    return xmin, D, alpha, loglikelihood, n, noise_flag

def power_law_ks_distance(data, alpha, xmin, xmax=None, discrete=False):
    """Data must be sorted beforehand!"""
    from numpy import arange
    data = data[data>=xmin]
    if xmax:
        data = data[data<=xmax]
    n = float(len(data))

    if not discrete:
        P = arange(n)/n
        CDF = 1-(xmin/data)**alpha
        D = max(abs(CDF-P))
    if discrete:
        from numpy import histogram, cumsum
        from scipy.special import zeta
        S = 1-cumsum(histogram(data,arange(xmin, max(data)+2))[0]/n)

        if xmax:
            P = (zeta(alpha, arange(xmin,xmax+1)) - zeta(alpha, xmax+1)) /\
                    (zeta(alpha, xmin)-zeta(alpha,xmax+1))
        if not xmax:
            P = zeta(alpha, arange(xmin,max(data)+1)) /\
                    zeta(alpha, xmin)

        D = max(abs(S-P))

    return D

def power_law_likelihoods(data, alpha, xmin, xmax=False, discrete=False):
    if alpha<0:
        from numpy import array
        return array([0])

    data = data[data>=xmin]
    if xmax:
        data = data[data<=xmax]

    if not discrete:
        likelihoods = (data**-alpha)/\
                ( (alpha-1) * xmin**(alpha-1) )
    if discrete:
        if alpha<1:
            from numpy import array
            return array([0])
        if not xmax:
            from scipy.special import zeta
            likelihoods = (data**-alpha)/\
                    zeta(alpha, xmin)
        if xmax:
            from scipy.special import zeta
            likelihoods = (data**-alpha)/\
                    (zeta(alpha, xmin)-zeta(alpha,xmax+1))
    from sys import float_info
    likelihoods[likelihoods==0] = 10**float_info.min_10_exp
    return likelihoods

def exponential_likelihoods(data, gamma, xmin, xmax=False, discrete=False):
    if gamma<0:
        from numpy import array
        return array([0])

    data = data[data>=xmin]
    if xmax:
        data = data[data<=xmax]

    from numpy import exp
    if not discrete:
        likelihoods = exp(-gamma*data)*\
                gamma*exp(gamma*xmin)
    if discrete:
        if not xmax:
            likelihoods = exp(-gamma*data)*\
                    (1-exp(-gamma))*exp(gamma*xmin)
        if xmax:
            likelihoods = exp(-gamma*data)*\
                    (1-exp(-gamma))/(exp(-gamma*xmin)-exp(-gamma*(xmax+1)))
    from sys import float_info
    likelihoods[likelihoods==0] = 10**float_info.min_10_exp
    return likelihoods

def truncated_power_law_likelihoods(data, alpha, gamma, xmin, xmax=False, discrete=False):
    if alpha<0 or gamma<0:
        from numpy import array
        return array([0])

    data = data[data>=xmin]
    if xmax:
        data = data[data<=xmax]

    from numpy import exp
    if not discrete:
        from mpmath import gammainc
        likelihoods = (data**-alpha)*exp(-gamma*data)*\
                (gamma**(1-alpha))/\
                float(gammainc(1-alpha,gamma*xmin))
    if discrete:
        if xmax:
            from numpy import arange
            X = arange(xmin, xmax+1)
            PDF = (X**-alpha)*exp(-gamma*X)
            PDF = PDF/sum(PDF)
            likelihoods = PDF[(data-xmin).astype(int)]
    from sys import float_info
    likelihoods[likelihoods==0] = 10**float_info.min_10_exp
    return likelihoods

def lognormal_likelihoods(data, mu, sigma, xmin, xmax=False, discrete=False, force_positive_mean=False):
    if sigma<0:
        from numpy import array
        return array([0])
    if force_positive_mean and mu<0:
        from numpy import array
        return array([0])

    data = data[data>=xmin]
    if xmax:
        data = data[data<=xmax]

    if not discrete:
        from numpy import sqrt, exp, log
        from scipy.special import erfc
        from scipy.constants import pi
        likelihoods = (1.0/data)*exp(-( (log(data) - mu)**2 )/2*sigma**2)*\
                sqrt(2/(pi*sigma**2))/erfc( (log(xmin)-mu) / (sqrt(2)*sigma))
    if discrete:
        if xmax:
            from numpy import exp, arange,log
            X = arange(xmin, xmax+1)
            PDF = (1.0/X)*exp(-( (log(X) - mu)**2 ) / 2*sigma**2)
            PDF = PDF/sum(PDF)
            likelihoods = PDF[(data-xmin).astype(int)]
    from sys import float_info
    likelihoods[likelihoods==0] = 10**float_info.min_10_exp
    return likelihoods

def hist_log(data, max_size, min_size=1, show=True):
    """hist_log does things"""
    from numpy import logspace, histogram
    from math import ceil, log10
    import pylab
    log_min_size = log10(min_size)
    log_max_size = log10(max_size)
    number_of_bins = ceil((log_max_size-log_min_size)*10)
    bins=logspace(log_min_size, log_max_size, num=number_of_bins)
    hist, edges = histogram(data, bins, density=True)
    if show:
        pylab.plot(edges[:-1], hist, 'o')
        pylab.gca().set_xscale("log")
        pylab.gca().set_yscale("log")
        pylab.show()
    return (hist, edges)
