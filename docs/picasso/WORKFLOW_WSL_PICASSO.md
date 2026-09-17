# PC/WSL ↔ Picasso workflow

Assume the browser downloads files into the Windows Downloads directory.

In WSL, this is normally:

```bash
/mnt/c/Users/<WINDOWS_USER>/Downloads
```

The examples below use the current Picasso migration hostname
`picasso3.scbi.uma.es`.

## 1. PC → Picasso

From WSL:

```bash
cd /mnt/c/Users/<WINDOWS_USER>/Downloads

scp PyEXPINT_Picasso_DevBundle_v0.8.2-dev.tar.gz \
    <PICASSO_USER>@picasso3.scbi.uma.es:~/
```

For larger future `.sif` files, prefer resumable `rsync`:

```bash
rsync -avP pyexpint_toms_v1.0.0.sif \
    <PICASSO_USER>@picasso3.scbi.uma.es:~/pyexpint_toms/incoming/
```

## 2. One-time Picasso installation

```bash
ssh <PICASSO_USER>@picasso3.scbi.uma.es

tar -xzf ~/PyEXPINT_Picasso_DevBundle_v0.8.2-dev.tar.gz -C ~
cd ~/PyEXPINT_Picasso_DevBundle_v0.8.2-dev

bash bootstrap_install.sh
```

The installer creates/updates:

```text
$HOME/pyexpint_toms/
```

and places the active source under:

```text
$HOME/pyexpint_toms/repo/
```

## 3. Check the environment

```bash
bash ~/pyexpint_toms/ops/scripts/01_check_picasso_env.sh
```

This is a quick login-node check only. It does not run a benchmark.

## 4. Stage one immutable campaign to FSCRATCH

Choose a descriptive ID, for example:

```bash
CAMPAIGN_ID=cpu2d_intel_v080_20260828a

bash ~/pyexpint_toms/ops/scripts/02_stage_campaign.sh "$CAMPAIGN_ID"
```

Never reuse a campaign ID.

## 5. Submit

```bash
# Final publication timing:
bash ~/pyexpint_toms/ops/scripts/03_submit_toms_timing.sh "$CAMPAIGN_ID"
```

## 6. Monitor

```bash
bash ~/pyexpint_toms/ops/scripts/04_status_campaign.sh "$CAMPAIGN_ID"
```

or directly:

```bash
squeue -l
```

## 7. Collect to HOME

Only after the array has finished:

```bash
bash ~/pyexpint_toms/ops/scripts/05_collect_campaign.sh "$CAMPAIGN_ID"
```

Persistent output appears under:

```text
~/pyexpint_toms/results/campaigns/$CAMPAIGN_ID/
```

Verify:

```bash
cd ~/pyexpint_toms/results/campaigns/$CAMPAIGN_ID
sha256sum -c MANIFEST.sha256
```

## 8. Remove FSCRATCH copy

First dry run:

```bash
bash ~/pyexpint_toms/ops/scripts/06_cleanup_fscratch.sh "$CAMPAIGN_ID"
```

Then, only after successful verification:

```bash
bash ~/pyexpint_toms/ops/scripts/06_cleanup_fscratch.sh "$CAMPAIGN_ID" --yes
```

## 9. Picasso → PC

From WSL:

```bash
cd /mnt/c/Users/<WINDOWS_USER>/Downloads

scp -r \
  <PICASSO_USER>@picasso3.scbi.uma.es:~/pyexpint_toms/results/campaigns/cpu2d_intel_v080_20260828a \
  .
```

For large result collections use `rsync -avP`.

## Important rule

Never use a file existing only in FSCRATCH as the unique copy of a paper result.
