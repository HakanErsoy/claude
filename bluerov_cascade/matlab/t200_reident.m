%% T200 thruster re-identification (MATLAB + System Identification Toolbox)
%
% Data: "MATLAB and Simulink Robotics Arena: From Data to Model", File Exchange 65919
% (MathWorks, 2018), folder T200_Dataset: 12 records, Ts = 2 ms, columns
% time (s), input (us), force (lb). The licence of that submission restricts its use to
% MathWorks products, so this identification is done in MATLAB; the data are not stored in
% the repository.
%
% What the JESTECH paper did (and the File Exchange script does): remove the means, low-pass
% filter, and fit one linear model, tfest(..., 4, 2), on ONE record (square, 0-10 Hz,
% 1600-1900 us). A linear model of mean-removed data cannot represent the dead band, the
% quadratic thrust-speed relation or the operating-point dependence, and one record cannot
% show whether it generalizes to other amplitudes.
%
% This script:
%   1. loads all 12 T200 records (no mean removal: the level matters);
%   2. calibrates the force scale of the test rig against the manufacturer's bollard curve
%      (load cell on a frame, unit "lb": the scale factor is estimated, not assumed);
%   3. fits four model classes on the same estimation record as JESTECH:
%        M0  linear tfest(4,2) on mean-removed data            (the JESTECH model)
%        M1  Hammerstein: static T200 curve, then 1st order + delay
%        M2  Hammerstein: static T200 curve, then 2nd order + delay
%        M3  Wiener (physical): motor speed with 1st-order lag + delay, thrust ~ speed^2
%   4. validates every model on the other 11 records (absolute level, NRMSE fit %);
%   5. writes t200_reident_fits.csv and t200_reident_params.csv for the simulator.
%
% Requirements: MATLAB R2021b or newer, System Identification Toolbox.
% Usage: put this file, T200_Dataset/ and the Blue Robotics spreadsheet
% (T200-Public-Performance-Data-10-20V-September-2019.xlsx, from
% https://cad.bluerobotics.com/) in one folder, then run t200_reident.

clear; close all;
Ts = 0.002;
LB2N = 4.44822;
dataDir = 'T200_Dataset';
btFile = 'T200-Public-Performance-Data-10-20V-September-2019.xlsx';

%% 1. Load all records
files = dir(fullfile(dataDir, 'T200_*.csv'));
rec = struct('name', {}, 'u', {}, 'F', {}, 'type', {});
for k = 1:numel(files)
    M = readmatrix(fullfile(dataDir, files(k).name));       % header line skipped
    M = M(all(isfinite(M(:, 2:3)), 2), :);
    rec(end+1).name = erase(files(k).name, '.csv'); %#ok<SAGROW>
    rec(end).u = M(:, 2);                                     % PWM [us]
    rec(end).F = M(:, 3);                                     % raw load-cell reading ("lb")
    rec(end).type = ternary(contains(files(k).name, 'Square'), 'square', 'sine');
end
estName = 'T200_Square_0-10_Hz_1600-1900_us';                % the JESTECH estimation record
iEst = find(strcmp({rec.name}, estName));
fprintf('%d records loaded, estimation record: %s\n', numel(rec), estName);

%% 2. Static curve and force-scale calibration
% Manufacturer bollard curves (PWM -> kgf) at several voltages; choose the voltage and the
% scale c such that c * raw ~ F_bt(PWM) in the settled parts of the square-wave records.
volts = [12 14 16 18 20];
settled = [];                                                 % [pwm, raw force] pairs
for k = find(strcmp({rec.type}, 'square'))
    u = rec(k).u; F = rec(k).F;
    edges = [1; find(diff(u) ~= 0) + 1; numel(u) + 1];
    for e = 1:numel(edges) - 1
        idx = edges(e):edges(e + 1) - 1;
        if numel(idx) > 100                                   % plateaus longer than 0.2 s
            tail = idx(round(0.6 * numel(idx)):end);          % last 40 %: settled
            settled(end+1, :) = [u(idx(1)), mean(F(tail))]; %#ok<SAGROW>
        end
    end
end
best = struct('err', inf);
for v = volts
    T = readmatrix(btFile, 'Sheet', sprintf('%d V', v));
    pwm = T(:, 1); Fbt = T(:, 6) * 9.80665;                   % N
    Fs = interp1(pwm, Fbt, settled(:, 1), 'linear', 'extrap');
    cb = [settled(:, 2), ones(size(settled, 1), 1)] \ Fs;     % scale and load-cell offset
    err = rms([settled(:, 2), ones(size(settled, 1), 1)] * cb - Fs);
    fprintf('  %2d V: scale %.3f N per unit, offset %.2f N, settled RMS error %.2f N\n', v, cb(1), cb(2), err);
    if err < best.err
        best = struct('err', err, 'volt', v, 'c', cb(1), 'b', cb(2), 'pwm', pwm, 'Fbt', Fbt);
    end
end
fprintf('static curve: %d V, force scale %.3f N per raw unit (lb would be %.3f), offset %.2f N\n', ...
        best.volt, best.c, LB2N, best.b);
Fstat = @(u) interp1(best.pwm, best.Fbt, u, 'linear', 'extrap');
for k = 1:numel(rec)
    rec(k).Fn = best.c * rec(k).F + best.b;                   % calibrated force [N]
end

%% 3. Models on the estimation record
est = rec(iEst);

% M0: the JESTECH / File Exchange model (mean removed, filtered, tfest 4/2)
d0 = detrend(iddata(est.Fn, est.u, Ts), 0);
d0f = idfilt(d0, 5, 0.064399);
M0 = tfest(d0f, 4, 2);
fprintf('M0 poles %s, zeros %s\n', mat2str(pole(M0)', 4), mat2str(zero(M0)', 4));

% M1, M2: Hammerstein with the static curve as a fixed input nonlinearity, delay estimated
dH = iddata(est.Fn, Fstat(est.u), Ts);
opt = tfestOptions('InitialCondition', 'estimate');
M1 = tfest(dH, 1, 0, NaN, opt);
M2 = tfest(dH, 2, 0, NaN, opt);

% M3: Wiener, physically motivated: normalized speed command -> 1st-order lag + delay -> F
% The speed command is the square root of the static thrust (thrust ~ speed^2), with sign.
sq = @(F) sign(F) .* sqrt(abs(F));
dW = iddata(sq(est.Fn), sq(Fstat(est.u)), Ts);
M3lin = tfest(dW, 1, 0, NaN, opt);

% Every model is simulated from rest at the first sample's operating point (the records start
% on a held command), so all four are compared under the same initial-condition assumption.
predict = @(k) [rec(k).Fn(1) + simdev(M0, rec(k).u, Ts), ...
                simdev(M1, Fstat(rec(k).u), Ts, true), ...
                simdev(M2, Fstat(rec(k).u), Ts, true), ...
                sqinv(simdev(M3lin, sq(Fstat(rec(k).u)), Ts, true))];

%% 4. Validation on all records (absolute level)
names = {rec.name}';
fit = zeros(numel(rec), 4);
for k = 1:numel(rec)
    y = rec(k).Fn;
    Y = predict(k);
    for m = 1:4
        fit(k, m) = 100 * (1 - norm(y - Y(:, m)) / norm(y - mean(y)));   % NRMSE fit [%]
    end
end
Tfit = array2table(fit, 'VariableNames', {'M0_tfest42', 'M1_hammer1', 'M2_hammer2', 'M3_wiener1'}, ...
                   'RowNames', names);
disp(Tfit);
writetable(Tfit, 't200_reident_fits.csv', 'WriteRowNames', true);
fprintf('median fit on the 11 validation records: M0 %.1f  M1 %.1f  M2 %.1f  M3 %.1f %%\n', ...
        median(fit(setdiff(1:end, iEst), :)));

%% 5. Parameters for the simulator (rovc/thruster.py)
[num1, den1] = tfdata(M1, 'v');                               % b / (s + a): tau = 1/a, gain = b/a
[num3, den3] = tfdata(M3lin, 'v');
p = table;
p.model = {'M1_hammer1'; 'M3_wiener1'};
p.tau_s = [den1(1) / den1(2); den3(1) / den3(2)];
p.gain = [num1(end) / den1(end); num3(end) / den3(end)];
p.delay_s = [M1.IODelay; M3lin.IODelay];
p.volt = [best.volt; best.volt];
p.force_scale = [best.c; best.c];
disp(p);
writetable(p, 't200_reident_params.csv');
[wn2, z2] = damp(M2);
fprintf('M2: natural frequencies %s rad/s, damping %s, delay %.3f s\n', mat2str(wn2', 3), mat2str(z2', 3), M2.IODelay);

%% Plots: estimation record and one record of each other amplitude
figure('Name', 'T200 re-identification');
show = [iEst, find(contains(names, '1650-1850') & contains(names, 'Sine_0-10')), ...
        find(contains(names, '1700-1800') & contains(names, 'Square_0-10'))];
for j = 1:numel(show)
    k = show(j); t = (0:numel(rec(k).u) - 1)' * Ts;
    subplot(numel(show), 1, j);
    Y = predict(k);
    plot(t, rec(k).Fn, 'k', t, Y(:, 1), '--', t, Y(:, 2), '-.', t, Y(:, 4), ':');
    xlim([0 6]); ylabel('F [N]'); title(strrep(names{k}, '_', ' '));
end
legend('measured', 'M0 linear 4/2 (JESTECH)', 'M1 Hammerstein', 'M3 Wiener'); xlabel('t [s]');
saveas(gcf, 't200_reident.png');

%% helpers
function y = simdev(sys, x, Ts, absolute)
% Response to x(t) - x(1) from rest; with absolute = true the steady output at x(1) is added.
    yd = sim(sys, iddata([], x - x(1), Ts));
    y = yd.y;
    if nargin > 3 && absolute
        y = y + dcgain(sys) * x(1);
    end
end

function F = sqinv(z)
    F = sign(z) .* z .^ 2;                                    % thrust ~ speed^2
end

function out = ternary(c, a, b)
    if c, out = a; else, out = b; end
end
