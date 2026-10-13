# ZTE Axon M (Z999 / fujisan) partition table

Read from an AT&T Axon M with `scripts/Get-PartitionTable.ps1` (firehose `getgptmainbackup`, read-only). eMMC, 512-byte sectors, single physical partition (0). Partition GUIDs are left out because they are unique to each phone.

Other variants (DoCoMo Z-01K, China, TIM) may differ. Run option 6 in the tool to check your own phone before flashing.

| Partition | Start sector | End sector | Sectors | Size (KB) |
|---|---:|---:|---:|---:|
| xbl | 131072 | 139263 | 8192 | 4096 |
| xblbak | 139264 | 147455 | 8192 | 4096 |
| tz | 147456 | 151551 | 4096 | 2048 |
| rpm | 151552 | 152575 | 1024 | 512 |
| hyp | 152576 | 153599 | 1024 | 512 |
| fbop | 262144 | 262399 | 256 | 128 |
| pmic | 393216 | 394239 | 1024 | 512 |
| fsg | 394240 | 398335 | 4096 | 2048 |
| modem | 398336 | 592895 | 194560 | 97280 |
| modemst1 | 655360 | 659455 | 4096 | 2048 |
| modemst2 | 659456 | 663551 | 4096 | 2048 |
| cdt | 786432 | 786433 | 2 | 1 |
| reserve | 786440 | 786503 | 64 | 32 |
| ddr | 786504 | 788551 | 2048 | 1024 |
| sec | 788552 | 788583 | 32 | 16 |
| ztecfg | 917504 | 918527 | 1024 | 512 |
| aboot | 1048576 | 1050623 | 2048 | 1024 |
| boot | 1050624 | 1181695 | 131072 | 65536 |
| **recovery** | 1181696 | 1312767 | 131072 | 65536 |
| system | 1312768 | 14944255 | 13631488 | 6815744 |
| keymaster | 14944256 | 14945279 | 1024 | 512 |
| cmnlib | 14945280 | 14945791 | 512 | 256 |
| cmnlib64 | 14945792 | 14946303 | 512 | 256 |
| dsp | 14946304 | 14979071 | 32768 | 16384 |
| dip | 14979072 | 14981119 | 2048 | 1024 |
| mdtp | 14981120 | 15046655 | 65536 | 32768 |
| devinfo | 15046656 | 15046657 | 2 | 1 |
| apdp | 15046664 | 15047175 | 512 | 256 |
| msadp | 15047176 | 15047687 | 512 | 256 |
| dpo | 15047688 | 15047689 | 2 | 1 |
| splash | 15047696 | 15114543 | 66848 | 33424 |
| echarge | 15114544 | 15196463 | 81920 | 40960 |
| bluetooth | 15196464 | 15198511 | 2048 | 1024 |
| fsc | 15204352 | 15204353 | 2 | 1 |
| ssd | 15204360 | 15204375 | 16 | 8 |
| cache | 15204376 | 18561047 | 3356672 | 1678336 |
| persist | 18561048 | 18626583 | 65536 | 32768 |
| misc | 18626584 | 18628631 | 2048 | 1024 |
| keystore | 18628632 | 18629655 | 1024 | 512 |
| devcfg | 18629656 | 18629911 | 256 | 128 |
| frp | 18629912 | 18630935 | 1024 | 512 |
| fingerid | 18630936 | 18639127 | 8192 | 4096 |
| ztebak1 | 18639128 | 18647319 | 8192 | 4096 |
| cryptkey | 18647320 | 18648343 | 1024 | 512 |
| lksecapp | 18743296 | 18743551 | 256 | 128 |
| sti | 18874368 | 18878463 | 4096 | 2048 |
| dcmlog | 18878464 | 19083263 | 204800 | 102400 |
| userdata | 19083264 | 122142686 | 103059423 | 51529711.5 |

## Notes

- `recovery` starts at sector **1181696** (byte offset `0x24100000`) and is 131072 sectors (64 MB). `config/rawprogram0.xml` uses exactly this.
- The `rawprogram0.xml` in the original TWRP download used `start_sector="210048"`. A 64 MB image written there covers sectors 210048 to 341119, which overlaps the `fbop` partition (262144 to 262399) and unallocated space. It never touches `recovery`.
