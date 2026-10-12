% Cross-check of the original EXPINT (2005) MATLAB package against PyEXPINT.
%
% Usage (Octave >= 8 or MATLAB), from any directory:
%     EXPINT_DIR=/path/to/expint CROSSCHECK_OUT=/path/to/results octave-cli crosscheck_expint.m
% EXPINT_DIR must contain the original common/ and schemes/ folders (not redistributed here).
% Then run compare_with_pyexpint.py on the same output directory.
%
% Writes to CROSSCHECK_OUT (default ./results):
%   expint_values.csv   final values of every scheme and of four one-line corrections on two problems
%   expint_orders.txt   observed orders of the original and corrected schemes
%   mgl45_coeffs.csv    coefficient functions of modgenlawson45 evaluated at z = -0.3
expint = getenv('EXPINT_DIR');
if isempty(expint), error('set EXPINT_DIR to the EXPINT 2005 package directory'); end
out = getenv('CROSSCHECK_OUT'); if isempty(out), out = fullfile(pwd, 'results'); end
if ~exist(out, 'dir'), mkdir(out); end
fixed = fullfile(out, 'corrected_schemes');
if ~exist(fixed, 'dir'), mkdir(fixed); end
corrections = {
  'etd2rk',    'b = { phi_1 - 2*phi_2,   phi_2 };',               'b = { phi_1 - phi_2,   phi_2 };';
  'etd2cf3',   'phi_12               = phipade(1/2*z, 1);',       'phi_12               = phipade(1/3*z, 1);';
  'etd5rkf',   'ez34 = exp(3 * z / 5);',                         'ez34 = exp(3 * z / 4);';
  'ablawson2', 'v = {  ez, -1/2*ez2; ...',                       'v = {  ez, -1/2*e2z; ...' };
for k = 1:size(corrections, 1)
  name = corrections{k, 1};
  src = fileread(fullfile(expint, 'schemes', [name '.m']));
  if numel(strfind(src, corrections{k, 2})) ~= 1, error('pattern not found exactly once in %s.m', name); end
  txt = strrep(src, corrections{k, 2}, corrections{k, 3});
  txt = strrep(txt, ['= ' name '(z, problem)'], ['= ' name '_corrected(z, problem)']);
  fid = fopen(fullfile(fixed, [name '_corrected.m']), 'w'); fwrite(fid, txt); fclose(fid);
end
addpath(fullfile(expint, 'common')); addpath(fullfile(expint, 'schemes')); addpath(fixed);
warning('off', 'all');

files = dir(fullfile(expint, 'schemes', '*.m'));
names = sort(cellfun(@(f) f(1:end-2), {files.name}, 'UniformOutput', false));
names = [names, cellfun(@(c) [c '_corrected'], corrections(:, 1)', 'UniformOutput', false)];
ex1 = @(t) 1 ./ (1 + 1.5 * exp(t));
fid = fopen(fullfile(out, 'expint_values.csv'), 'w'); fprintf(fid, 'scheme,problem,y1,y2\n');
for k = 1:numel(names)
  s = names{k};
  PS = struct('L', -1, 'N', @(u, t, p) u.^2, 'y0', 0.4, 'x', 0, 'exactsolution', @(x, t, p) ex1(t));
  [~, u] = expglm(PS, [0 1.6], 0.1, s); fprintf(fid, '%s,S,%.17g,nan\n', s, real(u(end)));
  PM = struct('L', [-1 0.3; 0.2 -2], 'N', @(u, t, p) u.^2, 'y0', [0.4; 0.3], 'x', [0; 0]);
  [~, u] = expglm(PM, [0 1.6], 0.1, s); fprintf(fid, '%s,M,%.17g,%.17g\n', s, real(u(end, 1)), real(u(end, 2)));
end
fclose(fid);

fid = fopen(fullfile(out, 'expint_orders.txt'), 'w');
hs = [0.2 0.1 0.05 0.025]; T = 1.6;
for a = [-1 -5]
  C = 1 / 0.4 + 1 / a; ex = @(t) 1 ./ (C * exp(-a * t) - 1 / a);
  fprintf(fid, '\n== y'' = %g y + y^2, y(0) = 0.4, T = 1.6, scalar L, exact startup; h = %s ==\n', a, mat2str(hs));
  for s = {'etd4rk', 'etd2rk', 'etd2rk_corrected', 'etd2cf3', 'etd2cf3_corrected', 'etd5rkf', 'etd5rkf_corrected', ...
           'ablawson2', 'ablawson2_corrected', 'modgenlawson45'}
    P = struct('L', a, 'N', @(u, t, p) u.^2, 'y0', 0.4, 'x', 0, 'exactsolution', @(x, t, p) ex(t));
    e = zeros(size(hs));
    for k = 1:numel(hs), [~, u] = expglm(P, [0 T], hs(k), s{1}); e(k) = abs(real(u(end)) - ex(T)); end
    fprintf(fid, '%-20s errors %s | slopes %s\n', s{1}, sprintf('%9.2e ', e), sprintf('%6.2f ', log2(e(1:end-1) ./ e(2:end))));
  end
end
n = 40; lam = -((1:n)' .^ 2) * pi^2 * 0.01;
P = struct('L', lam, 'N', @(u, t, p) 0.5 * (1 - u.^2) .* cos(t), 'y0', 1 ./ (1:n)', 'x', zeros(n, 1));
[~, uref] = expglm(P, [0 1], 1 / 2560, 'etd2cf3_corrected'); uref = real(uref(:, end));
hs2 = [0.1 0.05 0.025 0.0125];
fprintf(fid, '\n== stiff diagonal system (vector L, 40 modes, max |h lambda| = %.1f at h = 0.1), reference: etd2cf3_corrected at h = 1/2560 ==\n', max(abs(lam)) * 0.1);
for s = {'etd2cf3', 'etd2cf3_corrected'}
  e = zeros(size(hs2));
  for k = 1:numel(hs2), [~, u] = expglm(P, [0 1], hs2(k), s{1}); e(k) = max(abs(real(u(:, end)) - uref)); end
  fprintf(fid, '%-20s errors %s | slopes %s\n', s{1}, sprintf('%9.2e ', e), sprintf('%6.2f ', log2(e(1:end-1) ./ e(2:end))));
end
fprintf(fid, '\n== etd5rkf, same problem (a = -1), identical decoupled components, h = 0.05: final value by storage of L ==\n');
for s = {'etd5rkf', 'etd5rkf_corrected'}
  Ps = struct('L', -1, 'N', @(u, t, p) u.^2, 'y0', 0.4, 'x', 0);
  Pv = struct('L', [-1; -1], 'N', @(u, t, p) u.^2, 'y0', [0.4; 0.4], 'x', [0; 0]);
  Pm = struct('L', [-1 0; 0 -1], 'N', @(u, t, p) u.^2, 'y0', [0.4; 0.4], 'x', [0; 0]);
  [~, us] = expglm(Ps, [0 T], 0.05, s{1}); [~, uv] = expglm(Pv, [0 T], 0.05, s{1}); [~, um] = expglm(Pm, [0 T], 0.05, s{1});
  fprintf(fid, '%-20s scalar %.15f  vector %.15f  matrix %.15f\n', s{1}, real(us(end)), real(uv(end, 1)), real(um(end, 1)));
end
hs3 = [0.1 0.05 0.025 0.0125 0.00625];
for a = [-1 -5]
  C = 1 / 0.4 + 1 / a; ex = @(t) 1 ./ (C * exp(-a * t) - 1 / a);
  P = struct('L', a, 'N', @(u, t, p) u.^2, 'y0', 0.4, 'x', 0, 'exactsolution', @(x, t, p) ex(t));
  e = zeros(size(hs3));
  for k = 1:numel(hs3), [~, u] = expglm(P, [0 T], hs3(k), 'modgenlawson45'); e(k) = abs(real(u(end)) - ex(T)); end
  fprintf(fid, '\n== modgenlawson45 (original), a = %g, h = %s ==\n%-20s errors %s | slopes %s\n', a, mat2str(hs3), 'modgenlawson45', ...
          sprintf('%9.2e ', e), sprintf('%6.2f ', log2(e(1:end-1) ./ e(2:end))));
end
fclose(fid);

[u, v, a, b, c] = modgenlawson45(-0.3, struct());
fid = fopen(fullfile(out, 'mgl45_coeffs.csv'), 'w'); fprintf(fid, 'matrix,i,j,value\n');
mats = {u, v, a, b}; tags = {'U', 'V', 'A', 'B'};
for q = 1:4
  M = mats{q};
  for i = 1:size(M, 1), for j = 1:size(M, 2)
    if ~isempty(M{i, j}), fprintf(fid, '%s,%d,%d,%.17g\n', tags{q}, i, j, full(M{i, j})); end
  end, end
end
fclose(fid);
printf('wrote %d schemes to %s\n', numel(names), out);
