(* Les films d'arcs, comme le __main__ de python/Arcs.py. Depuis ocaml/ :
     dune exec bin/arcs.exe                              les trois méthodes
     dune exec bin/arcs.exe -- rubans diagramme          certaines
   Chaque méthode vérifie les mots (verifie_arcs, verifie_diagramme) puis écrit ../imgs/<méthode>/film_*_ocaml.mp4.
   ffmpeg doit être dans le PATH, ou donné par FFMPEG. *)

open Ardoise

let ffmpeg = Option.value (Sys.getenv_opt "FFMPEG") ~default:"ffmpeg"
let tresses = [ ([ 4; 3; -1; -1; 2; -4; 1 ], "43m1m12m41"); ([ 1; -2; 1; -2; 1; -2; 3; -1; 2 ], "charge") ]

(* les méthodes : (vérification, film, options de dessin : rubans, liseré) *)
let methodes =
  [ ("rubans", ((fun t -> Arcs.verifie_arcs ~ecart_fixes:30. t), (fun t -> Arcs.cree ~ecart_fixes:30. t), true, false));
    ("rubans_gauche", ((fun t -> Arcs.verifie_arcs ~fixes:Arcs.Gauche t), (fun t -> Arcs.cree ~fixes:Arcs.Gauche t), true, false));
    ("diagramme", (Arcs.verifie_diagramme, (fun t -> Arcs.cree_diagramme t), false, true)) ]

let () =
  let choisies = match List.tl (Array.to_list Sys.argv) with [] -> List.map fst methodes | l -> l in
  List.iter
    (fun methode ->
      let verifie, cree, rubans, lisere = List.assoc methode methodes in
      let dossier = Filename.concat "../imgs" methode in
      if not (Sys.file_exists dossier) then Sys.mkdir dossier 0o755;
      List.iter
        (fun (entiers, nom) ->
          let debut = Unix.gettimeofday () in
          let tresse = Tresses.tresse_de_entiers entiers in
          if not (verifie tresse) then failwith (methode ^ " : mots faux sur " ^ nom);
          let fichier = Printf.sprintf "%s/film_%s_ocaml.mp4" dossier nom in
          Dessin.film_arcs ~ffmpeg ~rubans ~lisere (cree tresse) tresse fichier;
          Printf.printf "%s %s fait (%.1f s)\n%!" methode nom (Unix.gettimeofday () -. debut))
        tresses)
    choisies
