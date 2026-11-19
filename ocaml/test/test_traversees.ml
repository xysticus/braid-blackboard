(* Les flips par traversées (Maillage.delaunay_par_traversees, Film.lettre ~par_traversees:true) ne changent pas la forme
   des courbes : les mots relus sur le dessin sont ceux de l'action d'Artin après chaque lettre, sur quelques tresses. *)

open Ardoise

let mots_corrects entiers () =
  let tresse = Tresses.tresse_de_entiers entiers in
  let nb = 1 + List.fold_left (fun m (l : Tresses.sigma Tresses.lettre) -> max m l.indice) 1 tresse in
  let film = Film.cree ~hauteur:800. ~largeur:800. tresse in
  let en_mots l = List.map (fun m -> (m : Tresses.Reduit.t :> Tresses.mot_de_fn)) l in
  ignore
    (List.fold_left
       (fun (film, k) sigma ->
         let film = fst (Film.lettre ~par_traversees:true film sigma) in
         let attendu = Array.to_list (Tresses.calcule_autofn_de_tresse ~nb_trous:nb (List.filteri (fun j _ -> j <= k) tresse)) in
         let lus = List.filteri (fun j _ -> j < List.length attendu) (Film.mots film) in
         if en_mots lus <> en_mots attendu then Alcotest.failf "mots faux après la lettre %d" (k + 1);
         (film, k + 1))
       (film, 0) tresse)

let () =
  Alcotest.run "traversees"
    [
      ( "mots",
        List.map
          (fun (nom, e) -> Alcotest.test_case nom `Quick (mots_corrects e))
          [ ("référence", [ 4; 3; -1; -1; 2; -4; 1 ]); ("chargée", [ 1; -2; 1; -2; 1; -2; 3; -1; 2 ]);
            ("Δ5", [ 1; 2; 3; 4; 1; 2; 3; 1; 2; 1 ]); ("(σ1σ2⁻¹)³", [ 1; -2; 1; -2; 1; -2 ]) ] );
    ]
