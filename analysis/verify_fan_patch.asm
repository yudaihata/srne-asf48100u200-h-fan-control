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
