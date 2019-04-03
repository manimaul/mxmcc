#!/usr/bin/env sh

regions=(REGION_34
REGION_40
REGION_15
REGION_32
REGION_22
REGION_14
REGION_08
REGION_24
REGION_17
REGION_26
REGION_10
REGION_02
REGION_03
REGION_13
REGION_12
REGION_06
REGION_07
REGION_06
REGION_04
REGION_30)

for each in ${regions[@]}; do
    echo "rendering $each"
    python compiler.py $each
done

