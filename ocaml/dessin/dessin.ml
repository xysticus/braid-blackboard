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
        (Triangulation.Aretes.fold
           (fun (a : Triangulation.Arete.t) _ acc ->
             let u, v = (a :> int * int) in
             [| pos.(u); pos.(v) |] :: acc)
           (Triangulation.Maillage.aretes film.maillage) [])
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
