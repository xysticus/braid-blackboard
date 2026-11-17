(* Tests de l'étape 1 : réduction libre, action d'Artin, et comparaison avec le Python
   (reference_python.txt, écrit par genere_reference.py). *)

open Ardoise.Tresses

let entiers_de_reduit (r : Reduit.t) = entiers_de_mot (r :> mot)
let reduit_entiers l = entiers_de_reduit (Reduit.de_mot (List.map lettre_de_entier l))
let mot_entiers = Alcotest.(list int)

let test_reduction () =
  Alcotest.check mot_entiers "vide" [] (reduit_entiers []);
  Alcotest.check mot_entiers "x x⁻¹" [] (reduit_entiers [ 1; -1 ]);
  Alcotest.check mot_entiers "en cascade" [ 3 ] (reduit_entiers [ 1; 2; -2; -1; 3 ]);
  Alcotest.check mot_entiers "rien à faire" [ 1; 2; 1 ] (reduit_entiers [ 1; 2; 1 ]);
  Alcotest.check mot_entiers "après une annulation, la lettre d'avant revient en tête" [ 1; 3 ]
    (reduit_entiers [ 1; 2; -2; 2; -2; 3 ])

(* σ_i σ_i⁻¹ et σ_i⁻¹ σ_i agissent comme l'identité. *)
let test_inverse () =
  List.iter
    (fun t ->
      let a = auto_de_tresse ~nb_trous:4 (tresse_de_entiers t) in
      Alcotest.(check (array mot_entiers))
        (String.concat " " (List.map string_of_int t))
        (Array.map entiers_de_reduit (identite 4))
        (Array.map entiers_de_reduit a))
    [ [ 1; -1 ]; [ -2; 2 ]; [ 1; 2; 3; -3; -2; -1 ] ]

(* Relations de tresse : σ₁σ₂σ₁ = σ₂σ₁σ₂ et σ₁σ₃ = σ₃σ₁. *)
let test_relations () =
  let auto t = Array.map entiers_de_reduit (auto_de_tresse ~nb_trous:4 (tresse_de_entiers t)) in
  Alcotest.(check (array mot_entiers)) "σ₁σ₂σ₁ = σ₂σ₁σ₂" (auto [ 1; 2; 1 ]) (auto [ 2; 1; 2 ]);
  Alcotest.(check (array mot_entiers)) "σ₁σ₃ = σ₃σ₁" (auto [ 1; 3 ]) (auto [ 3; 1 ])

(* Une ligne : « lettres ; nombre de trous ; image / image / ... ». *)
let entiers s =
  String.split_on_char ' ' s |> List.map String.trim |> List.filter (( <> ) "") |> List.map int_of_string

let lit_ligne ligne =
  match String.split_on_char ';' ligne with
  | [ tresse; n; images ] ->
    (entiers tresse, int_of_string (String.trim n), List.map entiers (String.split_on_char '/' images))
  | _ -> failwith ("ligne mal formée : " ^ ligne)

let test_python () =
  let lignes = In_channel.with_open_text "reference_python.txt" In_channel.input_lines in
  List.iter
    (fun ligne ->
      let tresse, nb_trous, attendu = lit_ligne ligne in
      let obtenu = auto_de_tresse ~nb_trous (tresse_de_entiers tresse) in
      Alcotest.(check (list mot_entiers))
        (String.concat " " (List.map string_of_int tresse))
        attendu
        (Array.to_list (Array.map entiers_de_reduit obtenu)))
    lignes;
  Printf.printf "%d tresses comparées au Python\n" (List.length lignes)

let () =
  Alcotest.run "tresses"
    [ ( "groupe libre",
        [ Alcotest.test_case "réduction" `Quick test_reduction ] );
      ( "action d'Artin",
        [ Alcotest.test_case "σ σ⁻¹ = 1" `Quick test_inverse;
          Alcotest.test_case "relations de tresse" `Quick test_relations;
          Alcotest.test_case "comme le Python" `Quick test_python ] ) ]
