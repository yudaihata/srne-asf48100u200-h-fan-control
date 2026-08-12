    .sect ".text"
    .global _fan_patch_verification

_fan_patch_verification:
    CMP     AR6, #350
    CMP     AR6, #320
    ADDF32  R1H, #-350.0, R1H
    LRETR

    .global _fan_patch_5c_verification

_fan_patch_5c_verification:
    CMP     AR6, #400
    CMP     AR6, #370
    ADDF32  R1H, #-400.0, R1H
    LRETR

    .global _fan_curve_slope_verification

_fan_curve_slope_verification:
    ; Six public IEEE-754 binary32 slopes plus the excluded 5 C-span boundary.
    ; Each pair reconstructs R3H exactly as the stock MOVIZ/MOVXI sequence does.
    MOVIZ   R3, #0x3E4C       ; 0.2 high half
    MOVXI   R3H, #0xCCCD
    MOVIZ   R3, #0x3E6E       ; 0.233333334 high half
    MOVXI   R3H, #0xEEEF
    MOVIZ   R3, #0x3E8F       ; 0.28 high half (stock)
    MOVXI   R3H, #0x5C29
    MOVIZ   R3, #0x3EB3       ; 0.35 high half
    MOVXI   R3H, #0x3333
    MOVIZ   R3, #0x3EEE       ; 0.466666669 high half
    MOVXI   R3H, #0xEEEF
    MOVIZ   R3, #0x3F33       ; 0.7 high half
    MOVXI   R3H, #0x3333
    MOVIZ   R3, #0x3FB3       ; 1.4 high half; 45/50 C is not public
    MOVXI   R3H, #0x3333
    LRETR

    .global _fan_custom_origin_verification

_fan_custom_origin_verification:
    ; Boundary and non-profile values used to verify the custom CLI encoder.
    CMP     AR6, #380
    CMP     AR6, #350
    ADDF32  R1H, #-10.0, R1H
    NOP
    NOP
    ADDF32  R1H, #-380.0, R1H
    NOP
    NOP
    ADDF32  R1H, #-500.0, R1H
    LRETR
