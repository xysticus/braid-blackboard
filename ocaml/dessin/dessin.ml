open Ardoise
open Geometrie

type couleur = float * float * float

let couleurs = [| (1., 0., 0.); (0., 0.7, 0.); (0., 0., 1.); (0.7, 0.7, 0.); (0.7, 0., 0.7); (0., 0.7, 0.7) |]

(* Une polyligne : déplacement au premier point, segments jusqu'aux suivants, puis le trait. *)
let trace ctx points =
  if Array.length points > 0 then begin
    Cairo.move_to ctx points.(0).x points.(0).y;
    Array.iteri (fun k p -> if k > 0 then Cairo.line_to ctx p.x p.y) points;
    Cairo.stroke ctx
  end

let peint ?(hauteur = 400) ?(largeur = 400) ?(largeur_brin = 4.) ?(en_couleur = true) ?axe polylignes trous clou =
  let surface = Cairo.Image.create Cairo.Image.ARGB32 ~w:largeur ~h:hauteur in
  let ctx = Cairo.create surface in
  Cairo.set_source_rgb ctx 1. 1. 1.;
  Cairo.paint ctx;
  Cairo.set_line_cap ctx Cairo.ROUND;
  Cairo.set_line_join ctx Cairo.JOIN_ROUND;
  Option.iter
    (fun morceaux ->
      Cairo.set_line_width ctx (Float.max 1.5 (0.8 *. largeur_brin));
      Cairo.set_source_rgb ctx 0.45 0.45 0.45;
      List.iter (trace ctx) morceaux)
    axe;
  Cairo.set_line_width ctx largeur_brin;
  let couleurs = if en_couleur then couleurs else [| (0., 0., 0.) |] in
  List.iteri
    (fun i points ->
      let r, v, b = couleurs.(i mod Array.length couleurs) in
      Cairo.set_source_rgb ctx r v b;
      trace ctx points)
    polylignes;
  Cairo.set_source_rgb ctx 0. 0. 0.;
  List.iter
    (fun p ->
      Cairo.arc ctx p.x p.y ~r:largeur_brin ~a1:0. ~a2:(2. *. Float.pi);
      Cairo.fill ctx)
    (trous @ [ clou ]);
  surface

let cadre ?(lisse = true) ?largeur_brin ?(avec_aretes = true) ?ecart (film : Film.t) =
  let largeur_brin = Option.value largeur_brin ~default:(3. *. film.largeur /. 400.) in
  (* brins serrés : trait plus fin *)
  let largeur_brin =
    match ecart with Some e -> Float.min largeur_brin (Float.max 1. (0.7 *. e)) | None -> largeur_brin
  in
  let pos = film.maillage.pos in
  let axe =
    if avec_aretes then
      Some
        (* dans l'ordre rangé, comme le Python : là où deux arêtes se recouvrent, le gris anticrénelé dépend de
           l'ordre de tracé (arrondi à 8 bits) *)
        (List.map
           (fun ((a : Triangulation.Arete.t), _) ->
             let u, v = (a :> int * int) in
             [| pos.(u); pos.(v) |])
           (Triangulation.Aretes.bindings (Triangulation.Maillage.aretes film.maillage)))
    else None
  in
  peint ~hauteur:(int_of_float film.hauteur) ~largeur:(int_of_float film.largeur) ~largeur_brin ?axe
    (Film.polylignes ~lisse film)
    (Array.to_list (Film.positions_des_trous film))
    pos.(film.clou)

let encodeur = [ "-pix_fmt"; "yuv420p"; "-c:v"; "libsvtav1"; "-crf"; "30"; "-preset"; "10" ]

(* Écrit tout le tableau d'octets dans le tube (write_bigarray peut n'en écrire qu'une partie). *)
let ecrit_tout descr donnees =
  let n = Bigarray.Array1.dim donnees in
  let rec boucle debut = if debut < n then boucle (debut + Unix.write_bigarray descr donnees debut (n - debut)) in
  boucle 0

let film_triangule ?(ffmpeg = "ffmpeg") ?vitesse ?(pause = 0.5) ?largeur_brin ?hauteur ?largeur tresse fichier =
  let film = Film.cree ?hauteur ?largeur tresse in
  let l = int_of_float film.largeur and h = int_of_float film.hauteur in
  let arguments =
    [ ffmpeg; "-y"; "-loglevel"; "error"; "-f"; "rawvideo"; "-pix_fmt"; "bgra"; "-s"; Printf.sprintf "%dx%d" l h;
      "-r"; "25"; "-i"; "-"; "-vf"; "scale=trunc(iw/2)*2:trunc(ih/2)*2" ]
    @ encodeur @ [ fichier ]
  in
  let tube = Unix.open_process_args_out ffmpeg (Array.of_list arguments) in
  let descr = Unix.descr_of_out_channel tube in
  (* rien n'est écrit dans le canal lui-même : les images partent directement sur le descripteur *)
  let ecrit ?(fois = 1) surface =
    Cairo.Surface.flush surface;
    let donnees = Cairo.Image.get_data8 surface in
    for _ = 1 to fois do ecrit_tout descr donnees done
  in
  let fois secondes = int_of_float (Film.arrondi (25. *. secondes)) in
  ecrit ~fois:(fois pause) (cadre ?largeur_brin ~ecart:film.dispositions.(0).ecart film);
  (* chaque image attend la suivante : la dernière du film, seule, reste affichée plus longtemps *)
  let derniere = ref None in
  let rendu film ecart =
    Option.iter ecrit !derniere;
    derniere := Some (cadre ?largeur_brin ~ecart film)
  in
  let _film = List.fold_left (fun film sigma -> fst (Film.lettre ?vitesse ~rendu film sigma)) film tresse in
  Option.iter (ecrit ~fois:(fois (3. *. pause))) !derniere;
  match Unix.close_process_out tube with
  | Unix.WEXITED 0 -> ()
  | _ -> failwith ("ffmpeg n'a pas pu écrire " ^ fichier)

(* Films d'arcs. *)

let couleurs_arcs =
  [| (0.85, 0.15, 0.15); (0.10, 0.60, 0.15); (0.15, 0.25, 0.85); (0.75, 0.60, 0.05); (0.65, 0.15, 0.65);
     (0.05, 0.60, 0.65) |]

let cadre_arcs ?(rubans = false) ?(largeur_brin = 2.5) ?(avec_aretes = false) ?(lisere = false) (film : Arcs.t) =
  let surface = Cairo.Image.create Cairo.Image.ARGB32 ~w:(int_of_float film.largeur) ~h:(int_of_float film.hauteur) in
  let ctx = Cairo.create surface in
  Cairo.set_source_rgb ctx 1. 1. 1.;
  Cairo.paint ctx;
  Cairo.set_line_cap ctx Cairo.ROUND;
  Cairo.set_line_join ctx Cairo.JOIN_ROUND;
  let pos = film.maillage.pos in
  if avec_aretes then begin
    Cairo.set_source_rgb ctx 0.8 0.8 0.8;
    Cairo.set_line_width ctx 0.7;
    Triangulation.Aretes.iter
      (fun (a : Triangulation.Arete.t) _ -> let u, v = (a :> int * int) in trace ctx [| pos.(u); pos.(v) |])
      (Triangulation.Maillage.aretes film.maillage)
  end;
  List.iteri
    (fun k _ ->
      let p = if rubans then Arcs.ruban film k else Arcs.polyligne film k in
      let couleur = couleurs_arcs.(k mod Array.length couleurs_arcs) in
      let traits = if lisere then [ ((1., 1., 1.), 0.85 *. film.ecart); (couleur, 1.3) ] else [ (couleur, largeur_brin) ] in
      List.iter
        (fun ((r, v, b), largeur) ->
          Cairo.set_source_rgb ctx r v b;
          Cairo.set_line_width ctx largeur;
          trace ctx p)
        traits)
    film.courbes;
  List.iter
    (fun (sommets, gris) ->
      Cairo.set_source_rgb ctx gris gris gris;
      Array.iter
        (fun s ->
          Cairo.arc ctx pos.(s).x pos.(s).y ~r:4. ~a1:0. ~a2:(2. *. Float.pi);
          Cairo.fill ctx)
        sommets)
    [ (film.voyageurs, 0.); (film.fixes, 0.55) ];
  surface

let film_arcs ?(ffmpeg = "ffmpeg") ?(rubans = false) ?(pause = 0.5) ?(lisere = false) ?images (film : Arcs.t) tresse fichier =
  let l = int_of_float film.largeur and h = int_of_float film.hauteur in
  let arguments =
    [ ffmpeg; "-y"; "-loglevel"; "error"; "-f"; "rawvideo"; "-pix_fmt"; "bgra"; "-s"; Printf.sprintf "%dx%d" l h;
      "-r"; "25"; "-i"; "-" ]
    @ encodeur @ [ fichier ]
  in
  let tube = Unix.open_process_args_out ffmpeg (Array.of_list arguments) in
  let descr = Unix.descr_of_out_channel tube in
  let ecrit ?(fois = 1) film =
    let surface = cadre_arcs ~rubans ~lisere film in
    Cairo.Surface.flush surface;
    let donnees = Cairo.Image.get_data8 surface in
    for _ = 1 to fois do ecrit_tout descr donnees done
  in
  let fois secondes = int_of_float (Film.arrondi (25. *. secondes)) in
  ecrit ~fois:(fois pause) film;
  let film = List.fold_left (fun film sigma -> Arcs.lettre ?images ~rendu:(fun f -> ecrit f) film sigma) film tresse in
  (* comme le Python : la dernière image est écrite une fois par la lettre, puis pendant la pause finale *)
  ecrit ~fois:(fois (3. *. pause)) film;
  match Unix.close_process_out tube with
  | Unix.WEXITED 0 -> ()
  | _ -> failwith ("ffmpeg n'a pas pu écrire " ^ fichier)

(* L'escargot. *)

let cadre_escargot (escargot : Escargot.t) t =
  let l = escargot.largeur and h = escargot.hauteur and e = escargot.e in
  let surface = Cairo.Image.create Cairo.Image.ARGB32 ~w:(int_of_float l) ~h:(int_of_float h) in
  let ctx = Cairo.create surface in
  let fond = Cairo.Pattern.create_linear ~x0:0. ~y0:0. ~x1:0. ~y1:h in
  Cairo.Pattern.add_color_stop_rgb fond ~ofs:0. 0.66 0.80 0.52;
  Cairo.Pattern.add_color_stop_rgb fond ~ofs:1. 0.38 0.58 0.30;
  Cairo.set_source ctx fond;
  Cairo.paint ctx;
  Cairo.set_line_cap ctx Cairo.ROUND;
  Cairo.set_line_join ctx Cairo.JOIN_ROUND;
  let coquille = [| (0.47, 0.29, 0.14); (0.86, 0.75, 0.56); (0.33, 0.19, 0.09); (0.70, 0.52, 0.30) |] in
  let chair = (0.74, 0.65, 0.52) and cerne = (0.24, 0.15, 0.08) in
  let c = Escargot.centre_coquille escargot t in
  let rayon =
    Escargot.rayon_anneau escargot t
    +. (((float escargot.anneau *. Escargot.tours_faits escargot t) +. 1.5) *. escargot.ecart)
  in
  let largeur = 0.8 *. escargot.ecart in
  let trait points (r, v, b) epaisseur =
    Cairo.set_source_rgb ctx r v b;
    Cairo.set_line_width ctx epaisseur;
    trace ctx points
  in
  let lignes = List.init escargot.n (Escargot.polyligne escargot) in
  (* d'abord le corps (hors de la coquille), puis la coquille par-dessus ; les arcs des yeux ne montent pas dans
     la coquille *)
  List.iter
    (fun dedans ->
      List.iteri
        (fun k points ->
          if not (dedans && k >= escargot.anneau) then begin
            Cairo.save ctx;
            if dedans then Cairo.arc ctx c.x c.y ~r:rayon ~a1:0. ~a2:(2. *. Float.pi)
            else begin
              (* comme le Python : l'arc suit le rectangle sans nouveau chemin *)
              Cairo.rectangle ctx 0. 0. ~w:l ~h;
              Cairo.arc ctx c.x c.y ~r:rayon ~a1:0. ~a2:(2. *. Float.pi);
              Cairo.set_fill_rule ctx Cairo.EVEN_ODD
            end;
            Cairo.clip ctx;
            (* le corps : chair épaisse, les brins se fondent en pied *)
            let epaisseur = if dedans then largeur else 1.5 *. escargot.ecart in
            trait points cerne (epaisseur +. (1.6 *. e));
            trait points (if dedans then coquille.(k mod Array.length coquille) else chair) epaisseur;
            Cairo.restore ctx
          end)
        lignes)
    [ false; true ];
  (* les yeux *)
  let apparition = Escargot.lisse ((t -. 9.) /. 2.) in
  if apparition > 0. then
    Array.iteri
      (fun j v ->
        if j > escargot.anneau then begin
          let p = escargot.maillage.pos.(v) in
          Cairo.set_source_rgba ctx 0.12 0.08 0.05 apparition;
          Cairo.arc ctx p.x p.y ~r:(6. *. e) ~a1:0. ~a2:(2. *. Float.pi);
          Cairo.fill ctx;
          Cairo.set_source_rgba ctx 1. 1. 1. apparition;
          Cairo.arc ctx (p.x +. (2. *. e)) (p.y -. (2. *. e)) ~r:(1.8 *. e) ~a1:0. ~a2:(2. *. Float.pi);
          Cairo.fill ctx
        end)
      escargot.voyageurs;
  surface

let film_escargot ?(ffmpeg = "ffmpeg") ?(duree = 12.) ?(images_par_seconde = 25) ?(pause = 2.) escargot fichier =
  let l = int_of_float escargot.Escargot.largeur and h = int_of_float escargot.hauteur in
  let arguments =
    [ ffmpeg; "-y"; "-loglevel"; "error"; "-f"; "rawvideo"; "-pix_fmt"; "bgra"; "-s"; Printf.sprintf "%dx%d" l h;
      "-r"; string_of_int images_par_seconde; "-i"; "-" ]
    @ encodeur @ [ fichier ]
  in
  let tube = Unix.open_process_args_out ffmpeg (Array.of_list arguments) in
  let descr = Unix.descr_of_out_channel tube in
  let ips = float images_par_seconde in
  let nombre = int_of_float (Film.arrondi (duree *. ips)) in
  let rec boucle n escargot =
    if n <= nombre then begin
      let t = float n /. ips in
      let escargot =
        if n > 0 then Escargot.deplace escargot (Escargot.choregraphie escargot t) (2. *. escargot.e) else escargot
      in
      let surface = cadre_escargot escargot t in
      Cairo.Surface.flush surface;
      let donnees = Cairo.Image.get_data8 surface in
      for _ = 1 to if n < nombre then 1 else int_of_float (Film.arrondi (pause *. ips)) do ecrit_tout descr donnees done;
      boucle (n + 1) escargot
    end
  in
  boucle 0 escargot;
  match Unix.close_process_out tube with
  | Unix.WEXITED 0 -> ()
  | _ -> failwith ("ffmpeg n'a pas pu écrire " ^ fichier)

(* Le film conforme (film_conforme de python/Conforme.py, avec le raccord par triangulation et sans les arêtes de
   construction) : chaque image est peinte comme dans le Python (lacets décalés de la marge, trous, clou), et écrite
   au fil du calcul dans le tube vers ffmpeg, avec les mêmes arguments. La première image dure [pause] (500 ms), les
   suivantes 40 ms, la dernière 3 × pause. Rend les anomalies de la vérification. *)
let film_conforme ?(ffmpeg = "ffmpeg") ?(hauteur = 400) ?(largeur = 400) ?(marge = 0) ?(largeur_brin = 4.) ?(pause = 500.)
    ?(verifie = false) tresse fichier =
  let arguments =
    [ ffmpeg; "-y"; "-loglevel"; "error"; "-f"; "rawvideo"; "-pix_fmt"; "bgra"; "-s"; Printf.sprintf "%dx%d" largeur hauteur;
      "-r"; "25"; "-i"; "-" ]
    @ encodeur @ [ fichier ]
  in
  let tube = Unix.open_process_args_out ffmpeg (Array.of_list arguments) in
  let descr = Unix.descr_of_out_channel tube in
  let decalage = { x = float_of_int marge; y = float_of_int marge } in
  let surface (im : Film_conforme.image) =
    peint ~hauteur ~largeur ~largeur_brin
      (List.map (Array.map (fun p -> p +: decalage)) im.lignes)
      (List.map (fun p -> p +: decalage) (Array.to_list im.trous))
      (im.clou +: decalage)
  in
  let ecrit fois im =
    let s = surface im in
    Cairo.Surface.flush s;
    let donnees = Cairo.Image.get_data8 s in
    for _ = 1 to fois do ecrit_tout descr donnees done
  in
  (* nombre d'images de 40 ms pour une durée en millisecondes : max(1, round(ms / 40)), arrondi du Python *)
  let fois ms = max 1 (int_of_float (Film.arrondi (ms /. 40.))) in
  (* chaque image est écrite quand arrive la suivante : la dernière dure plus longtemps *)
  let rang = ref 0 and derniere = ref None in
  let rendu im =
    Option.iter (ecrit (fois (if !rang = 1 then pause else 40.))) !derniere;
    incr rang;
    derniere := Some im
  in
  let anomalies =
    Film_conforme.film ~verifie ~hauteur:(float_of_int hauteur) ~largeur:(float_of_int largeur) ~marge:(float_of_int marge)
      ~rendu tresse
  in
  Option.iter (ecrit (fois (3. *. pause))) !derniere;
  (match Unix.close_process_out tube with
  | Unix.WEXITED 0 -> ()
  | _ -> failwith ("ffmpeg n'a pas pu écrire " ^ fichier));
  anomalies
