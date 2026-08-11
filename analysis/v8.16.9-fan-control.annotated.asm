; V8.16.9 fan-control annotated disassembly excerpts
; ==================================================
;
; SOURCE_FILE: ASF48100SU200_V8.16.9.bin
; SOURCE_SIZE: 475136 bytes
; SOURCE_SHA256: d4b4f4590689ae2effedf40e3999da8d4b9dfdcac7a1eff4635d0eca6d644600
; ARCHITECTURE: TI TMS320C28x/C2000, little-endian 16-bit words
; LOAD_MAPPING: file offset 0 -> C28x word address 0x84000
; DISASSEMBLER: TI dis2000 25.11.1 LTS
; PURPOSE: minimal evidence excerpts for research, review, and cross-version work
; ASSEMBLABLE: no; omitted code and inline annotations are intentional
;
; Address conversion for this exact image only:
;   file_offset = (word_address - 0x84000) * 2
;
; NOTICE:
;   These limited excerpts are derived from proprietary SRNE firmware and are
;   included only as necessary evidence for commentary and analysis. They are
;   not a complete routine or firmware dump and are not covered by this
;   repository's MIT License. No rights to the underlying firmware are granted.
;
; Evidence labels used below:
;   [C] confirmed-static
;   [S] strongly-supported by multiple static anchors
;   [R] runtime-observed or supported by physical identification
;
; The complete recovered routine spans approximately 0x964B4..0x966B6. Only
; the blocks needed to substantiate the public fan-control findings are shown.

; -----------------------------------------------------------------------------
; [C] Scheduler call into the recovered fan-control routine
; -----------------------------------------------------------------------------
0009c515   7649   LCR          0x0964b4
0009c516   64b4

; -----------------------------------------------------------------------------
; [C] ePWM4B initialization anchor
;
; DP 0x10D / direct offset 0x23 resolves to the ePWM4 time-base period used by
; this target. 0x0D05 = 3333 counts. The surrounding setup and the runtime
; compare write below establish the channel; the constant alone is not enough.
; -----------------------------------------------------------------------------
00092640   761f   MOVW         DP, #0x10d
00092641   010d
00092642   2823   MOV          @0x23, #0x0d05      ; [C] period = 3333
00092643   0d05
00092644   2b21   MOV          @0x21, #0
; ... adjacent ePWM setup omitted ...
0009264b   761f   MOVW         DP, #0x10d
0009264c   010d
0009264d   2b2b   MOV          @0x2b, #0
0009264e   282d   MOV          @0x2d, #0x0d04
0009264f   0d04

; -----------------------------------------------------------------------------
; [C] Temperature hysteresis and persistence
;
; AR6 is the recovered internal-temperature request input in deci-degrees C.
; State bit @0x1C:0 is used by the temperature gate. With the recovered
; approximately 100 ms call cadence:
;   - 20 increments (0x14) correspond to about 2 s before start.
;   - the counter is loaded with 100 (0x64) and decremented while <= 42.0 C,
;     corresponding to about 10 s before stop.
;
; File offsets of the immediate continuation words:
;   0x96502 -> 0x24A04 (450)
;   0x96509 -> 0x24A12 (420)
; -----------------------------------------------------------------------------
00096501   1ba6   CMP          AR6, #450           ; [C] 45.0 C start threshold
00096502   01c2
00096503   6313   SB           19, GEQ             ; enter/start persistence path
; ... mode/override state selection retained but not reproduced ...
00096508   1ba6   CMP          AR6, #420           ; [C] 42.0 C stop threshold
00096509   01a4
0009650a   6209   SB           9, GT
0009650b   0b07   DEC          @0x7                ; [S] stop persistence counter
0009650c   6218   SB           24, GT
0009650d   b600   MOVB         XAR7, #0x00
0009650e   2b07   MOV          @0x7, #0
0009650f   181c   AND          @0x1c, #0xfffe      ; [C] clear temp-gate active
00096510   fffe
00096511   c32c   MOVL         @0x2c, XAR7         ; [S] clear filtered request
00096512   6f12   SB           18, UNC
00096513   56bf   MOVB         @0x7, #0x64, UNC    ; [C] hold/decrement seed = 100
00096514   6407
00096515   6f0f   SB           15, UNC
00096516   761f   MOVW         DP, #0x3d3
00096517   03d3
00096518   401c   TBIT         @0x1c, #0x0         ; gate already active?
00096519   6d0a   SB           10, TC
0009651a   0a07   INC          @0x7                ; [S] start persistence counter
0009651b   9307   MOV          AH, @0x7
0009651c   5314   CMPB         AH, #0x14           ; [C] 20 calls
0009651d   6407   SB           7, LT
0009651e   56bf   MOVB         @0x7, #0x64, UNC
0009651f   6407
00096520   1a1c   OR           @0x1c, #0x0001      ; [C] set temp-gate active
00096521   0001
00096522   6f02   SB           2, UNC
00096523   2b07   MOV          @0x7, #0

; -----------------------------------------------------------------------------
; [C/S] Temperature-to-demand curve
;
; Independent assembly confirms the ADDF32 instruction at 0x965BE encodes
; ADDF32 R1H,#-450.0,R1H. The split instruction words must not be decoded as a
; raw contiguous IEEE-754 value.
;
; Normalized recovered calculation:
;   request ~= (temperature_deci_c - 450) * 0.28 + 30
;
; This is 2.8 request points per degree C, with 30 at 45 C. The generic request
; is limited to 10..101 here; later output logic applies state-dependent lower
; duty behavior. File offset 0x24B7E is word address 0x965BF.
; -----------------------------------------------------------------------------
000965b2   3b01   SETC         SXM
000965b3   85a6   MOV          ACC, AR6
000965b4   bda9   MOV32        R0H, ACC
000965b5   0f12
000965ba   e689   I32TOF32     R1H, R0H
000965bb   0001
000965bc   e801   MOVIZ        R3, #0x3e8f        ; high half of 0.28
000965bd   f47b
000965be   e8b0   ADDF32       R1H, #0xc3e1, R1H ; [C] normalized: add -450.0
000965bf   f849
000965c0   e80a   MOVXI        R3H, #0x5c29       ; completes 0.28
000965c1   e14b
000965c2   e700   MPYF32       R0H, R3H, R1H
000965c3   0058
000965c5   e890   ADDF32       R0H, #0x41f0, R0H ; [C] add 30.0
000965c6   7c00
000965c8   e68c   F32TOI16     R0H, R0H
000965c9   0000
000965cc   bfa9   MOV32        ACC, R0H
000965cd   0f12
000965ce   93a9   MOV          AH, @AL
000965cf   960a   MOV          @0xa, AL           ; [S] temperature request
000965d0   5365   CMPB         AH, #0x65          ; [C] upper limit 101
000965d1   6403   SB           3, LT
000965d2   9a65   MOVB         AL, #0x65
000965d3   6f04   SB           4, UNC
000965d4   9a0a   MOVB         AL, #0x0a          ; [C] lower limit 10
000965d5   5672   MAX          AL, @AH
000965d6   00a8
000965d7   960a   MOV          @0xa, AL

; -----------------------------------------------------------------------------
; [S] Four-demand maximum and 1/32 smoothing
;
; Data-flow analysis identifies @0xA/@0xB/@0xC/@0xD as temperature, load,
; charge-related, and discharge-related requests. The helper at 0x9DAE3
; combines the first three; MAX includes the fourth. The fixed-point accumulator
; @0x2C is updated by one thirty-second of the target error.
; -----------------------------------------------------------------------------
000965d9   920a   MOV          AL, @0xa
000965da   5c0c   MOVZ         AR4, @0xc
000965db   930b   MOV          AH, @0xb
000965dc   7649   LCR          0x09dae3           ; [S] combine first 3 requests
000965dd   dae3
000965de   761f   MOVW         DP, #0x3d3
000965df   03d3
000965e0   3b01   SETC         SXM
000965e3   5672   MAX          AL, @0xd           ; [S] maximum including fourth
000965e4   000d
000965e5   25a9   MOV          ACC, AL << 16
000965e6   032c   SUBL         ACC, @0x2c
000965e7   ff44   SFR          ACC, 5             ; [C] divide error by 32
000965e8   5601   ADDL         @0x2c, ACC         ; [C] filtered += error / 32
000965e9   002c

; -----------------------------------------------------------------------------
; [C] Runtime ePWM4B compare write
;
; Intervening code converts/clamps the filtered request into @0x23. The write
; through base 0x4300 plus offset 0x6D is the ePWM4B compare-B update.
; -----------------------------------------------------------------------------
0009667c   9223   MOV          AL, @0x23
0009667d   8f40   MOVL         XAR5, #0x004300
0009667e   4300
0009667f   8aa5   MOVL         XAR4, XAR5
00096680   d06d   MOVB         XAR0, #0x6d
00096681   9695   MOV          *+XAR5[AR0], AL    ; [C] ePWM4B compare-B write
00096682   dc49   ADDB         XAR4, #73
00096683   18c4   AND          *+XAR4[0], #0xfff3
00096684   fff3

; -----------------------------------------------------------------------------
; [C/S/R] GPIO67 active-low fan-lock monitoring
;
; The GPIO input is tested only after the fan-active state test. With no fault
; active, a high input branches to counter reset; a low input increments to 50
; and sets the fault. With a fault active, sustained high decrements from 50 and
; clears the fault after the recovery interval. No edge counter, capture timer,
; period measurement, or RPM calculation appears in this path.
; -----------------------------------------------------------------------------
00096687   401e   TBIT         @0x1e, #0x0         ; [S] lock-fault state
00096688   6d1c   SB           28, TC              ; fault active -> recovery path
00096689   401c   TBIT         @0x1c, #0x0         ; [C] fan-active gate
0009668a   6c16   SB           22, NTC             ; stopped -> do not monitor
0009668b   761f   MOVW         DP, #0x1fc
0009668c   01fc
0009668d   4310   TBIT         @0x10, #0x3         ; [C/S/R] GPIO67 lock input
0009668e   6d12   SB           18, TC              ; high -> reset low counter
0009668f   761f   MOVW         DP, #0x3d3
00096690   03d3
00096691   0a09   INC          @0x9                ; low persistence
00096692   9209   MOV          AL, @0x9
00096693   5232   CMPB         AL, #0x32           ; [C] 50 calls ~= 5 s
00096694   6420   SB           32, LT
00096695   56bf   MOVB         @0x9, #0x32, UNC
00096696   3209
00096697   1a1e   OR           @0x1e, #0x0001      ; [C] set lock fault
00096698   0001
; ... existing error-report call omitted ...
000966a0   761f   MOVW         DP, #0x3d3
000966a1   03d3
000966a2   2b09   MOV          @0x9, #0            ; high/stopped counter reset
000966a3   6f11   SB           17, UNC
000966a4   761f   MOVW         DP, #0x1fc          ; fault-active recovery path
000966a5   01fc
000966a6   4310   TBIT         @0x10, #0x3
000966a7   6c09   SB           9, NTC              ; still low -> reload/hold
000966a8   761f   MOVW         DP, #0x3d3
000966a9   03d3
000966aa   0b09   DEC          @0x9                ; high recovery persistence
000966ab   6309   SB           9, GEQ
000966ac   181e   AND          @0x1e, #0xfffe      ; [C] clear lock fault
000966ad   fffe
000966ae   2b09   MOV          @0x9, #0
000966af   6f05   SB           5, UNC
000966b0   761f   MOVW         DP, #0x3d3
000966b1   03d3
000966b2   56bf   MOVB         @0x9, #0x32, UNC    ; hold recovery seed at 50
000966b3   3209
000966b4   fe82   SUBB         SP, #2

; -----------------------------------------------------------------------------
; Original project pseudocode (not vendor code)
; -----------------------------------------------------------------------------
;
; if !temp_gate_active:
;     if temperature_deci_c >= 450 for 20 calls:
;         temp_gate_active = true
;         persistence = 100
; else if temperature_deci_c <= 420:
;     if --persistence <= 0:
;         temp_gate_active = false
;         filtered_request = 0
;
; temperature_request = clamp(
;     (temperature_deci_c - 450) * 0.28 + 30,
;     10,
;     101,
; )
; target = max(temperature_request, load_request,
;              charge_request, discharge_request)
; filtered_request += (target - filtered_request) / 32
; ePWM4B_compare = state_dependent_scale_and_clamp(filtered_request)
;
; if fan_active:
;     if GPIO67 == LOW for 50 calls: set_fan_lock_fault()
;     if fault_active and GPIO67 == HIGH for 50 calls: clear_fan_lock_fault()
;
; Confidence boundary:
;   Exact instructions, words, addresses, and replacement encodings are static
;   evidence. Variable names and the approximately 100 ms cadence are recovered
;   semantics. Static evidence alone does not prove updater acceptance, safe
;   boot, another hardware revision, or runtime safety.
