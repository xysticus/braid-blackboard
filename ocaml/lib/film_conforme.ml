(* La boucle du film conforme (film_conforme de python/Conforme.py, sans le dessin ni le MP4, qui sont dans
   dessin/dessin.ml) et la vérification nb_croisements : étape 7d du plan OCaml. Le raccord est toujours celui par
   triangulation (le défaut du Python ; le mélange n'est pas traduit). Chaque image porte ses lignes de construction
   (l'axe et la ligne brisée L–A–B–R, avec leurs fondus pendant le raccord) ; le dessin Cairo ne les trace pas, la page web
   le fait si on le lui demande. *)

open Geometrie

type image = {
  lignes : point array list;
  trous : point array;
  clou : point;
  construction : (point * point * float) list;
      (** Les lignes de construction : des segments avec leur opacité (> 0), l'axe et A–B toujours à 1. *)
  ab : int;  (** l'indice dans [construction] du segment A–B (les morceaux de l'axe le précèdent) *)
  maillage : (point * point) list;
      (** Les arêtes de la triangulation sur laquelle les lacets sont posés pendant le raccord (vide hors du raccord, où le dessin est
          conforme) ; avec les arêtes qui vont au bord convexe, hors de l'image. *)
}
(* Une image du film, dans le cadre intérieur (avant le décalage de la marge). *)

type anomalie = { lettre : int; image : int; detail : string }

let lisse u = u *. u *. (3. -. (2. *. u))

(* Les lignes de construction d'une image au temps s (le [dessin_axe] du Python) : les morceaux de l'axe et A–B, puis
   L–A et B–R qui s'estompent (opacité 1 − poids) pendant que L–B et A–R apparaissent (opacité poids), poids étant la part
   du raccord : 0 sur la ligne brisée L–A–B–R de l'état k, 1 sur L–B–A–R de l'état k+1. Les segments invisibles sont omis. *)
let indice_ab l ~reduction s = List.length (fst (Conforme.aretes l ~reduction s))

let construction l ~reduction s ~poids =
  let axe, cinq = Conforme.aretes l ~reduction s in
  let avec alpha (p, q) = (p, q, alpha) in
  List.map (avec 1.) axe
  @ List.filter
      (fun (_, _, alpha) -> alpha > 0.)
      [ avec 1. cinq.(1); avec (1. -. poids) cinq.(0); avec (1. -. poids) cinq.(2); avec poids cinq.(3); avec poids cinq.(4) ]

(* Nombre de croisements entre lacets distincts, hors du voisinage du clou (où ils se rejoignent). Comme le Python :
   segments groupés par paquets de 64 avec leur rectangle englobant, on ne compare que les paquets qui se chevauchent. *)
let nb_croisements ?(rayon = 12.) lignes clou =
  let paquets = ref [] in
  List.iteri
    (fun l p ->
      let loin q = norme (q -: clou) > rayon in
      let segments =
        List.filter_map
          (fun k -> if loin p.(k) && loin p.(k + 1) then Some (p.(k), p.(k + 1)) else None)
          (List.init (max 0 (Array.length p - 1)) Fun.id)
        |> Array.of_list
      in
      let n = Array.length segments in
      let k = ref 0 in
      while !k < n do
        let paquet = Array.sub segments !k (min 64 (n - !k)) in
        let xs = Array.concat [ Array.map (fun (a, _) -> a.x) paquet; Array.map (fun (_, b) -> b.x) paquet ] in
        let ys = Array.concat [ Array.map (fun (a, _) -> a.y) paquet; Array.map (fun (_, b) -> b.y) paquet ] in
        let mini t = Array.fold_left Float.min Float.infinity t and maxi t = Array.fold_left Float.max Float.neg_infinity t in
        paquets := (l, paquet, (mini xs, mini ys), (maxi xs, maxi ys)) :: !paquets;
        k := !k + 64
      done)
    lignes;
  let paquets = Array.of_list (List.rev !paquets) in
  let total = ref 0 in
  for x = 0 to Array.length paquets - 1 do
    let la, pa, (minax, minay), (maxax, maxay) = paquets.(x) in
    for y = x + 1 to Array.length paquets - 1 do
      let lb, pb, (minbx, minby), (maxbx, maxby) = paquets.(y) in
      if la <> lb && not (minax > maxbx || minay > maxby || minbx > maxax || minby > maxay) then
        Array.iter
          (fun (p0, p1) ->
            let d = p1 -: p0 in
            Array.iter
              (fun (q0, q1) ->
                let f = q1 -: q0 and q = q0 -: p0 in
                let den = (d.x *. f.y) -. (d.y *. f.x) in
                if den <> 0. then begin
                  let t = ((q.x *. f.y) -. (q.y *. f.x)) /. den and u = ((q.x *. d.y) -. (q.y *. d.x)) /. den in
                  if t >= 0. && t < 1. && u >= 0. && u < 1. then incr total
                end)
              pb)
          pa
    done
  done;
  !total

(* Dessin de l'état e de la lettre l au temps s ; si les arcs sortent par le haut, on aplatit davantage (réduction) :
   rend les lignes et la réduction. En Python, [lettre.reduction] est un attribut modifié en place ; ici un argument. *)
let dessin_reduit (l : Conforme.lettre) e s =
  let essai = Conforme.dessin l ~reduction:1. e s in
  let y_min = List.fold_left (fun a p -> Array.fold_left (fun a q -> Float.min a q.y) a p) Float.infinity essai in
  if y_min < 10. then
    let reduction = (l.y_axe -. 10.) /. (l.y_axe -. y_min) in
    (Conforme.dessin l ~reduction e s, reduction)
  else (essai, 1.)

(* L'image finale de la tresse (l'image clé après la dernière lettre), dans le cadre intérieur : la lettre est celle de
   la dernière lettre, dessinée à la fin du demi-tour. Sert d'image fixe à la page web. *)
let image_finale ?(hauteur = 800.) ?(largeur = 800.) ?(marge = 60.) tresse =
  let n_lettres = List.length tresse in
  if n_lettres = 0 then invalid_arg "image_finale : tresse vide";
  let nb_trous = List.fold_left (fun a (l : _ Tresses.lettre) -> max a l.indice) 0 tresse + 1 in
  let prefixe n = List.filteri (fun i _ -> i < n) tresse in
  let etat n = Tresses.etat_de_tresse ~nb_trous (prefixe n) in
  let k = n_lettres - 1 in
  let l = Conforme.lettre ~hauteur:(hauteur -. (2. *. marge)) ~largeur:(largeur -. (2. *. marge)) (etat k) (etat (k + 1)) (List.nth tresse k) in
  let lignes, reduction = dessin_reduit l 1 1. in
  { lignes; trous = Conforme.trous_ecran l ~reduction 1.; clou = l.clou; construction = construction l ~reduction 1. ~poids:1.; ab = indice_ab l ~reduction 1.; maillage = [] }

(* Le film : pour chaque lettre, l'état k dessiné sur L–A–B–R, puis l'état k+1 sur L–B–A–R, raccordés autour de la
   verticale par la triangulation pendant la fenêtre (part du mouvement). [rendu] est appelé avec chaque image dans
   l'ordre (la première est l'image clé de départ). Le cadre intérieur fait (hauteur − 2 marge) × (largeur − 2 marge).
   verifie : relit les mots et compte les croisements sur chaque image. Rend les anomalies. L'ordre des calculs est
   celui du Python, y compris celui des appels qui remplissent le cache des cartes : les derniers chiffres en
   dépendent. *)
let film ?(images = 48) ?(fenetre = 0.5) ?(verifie = false) ?(sans_fantomes = false) ?(libre = false) ?(sans_maillage = false) ~hauteur ~largeur ~marge ~rendu tresse =
  let entiers = List.map Tresses.entier_de_lettre tresse in
  let nb_trous = (match entiers with [] -> 5 | _ -> List.fold_left (fun a x -> max a (abs x)) 0 entiers) + 1 in
  let h_int = hauteur -. (2. *. marge) and l_int = largeur -. (2. *. marge) in
  let prefixe n = List.filteri (fun i _ -> i < n) tresse in
  let etat n = Tresses.etat_de_tresse ~nb_trous (prefixe n) in
  let anomalies = ref [] in
  (* première image : l'image clé, dessinée elle aussi par la carte (descentes en géodésiques) *)
  let premiere = Conforme.lettre ~hauteur:h_int ~largeur:l_int (etat 0) (etat 1) (List.hd tresse) in
  rendu
    { lignes = Conforme.dessin premiere ~reduction:1. 0 0.; trous = Conforme.trous_ecran premiere ~reduction:1. 0.;
      clou = premiere.clou; construction = construction premiere ~reduction:1. 0. ~poids:0.; ab = indice_ab premiere ~reduction:1. 0.; maillage = [] };
  List.iteri
    (fun k sigma ->
      let l = Conforme.lettre ~hauteur:h_int ~largeur:l_int (etat k) (etat (k + 1)) sigma in
      let mots = List.map (fun j -> Array.to_list (Tresses.calcule_autofn_de_tresse ~nb_trous (prefixe (k + j)))) [ 0; 1 ] in
      let temps = Array.init (images + 1) (fun n -> lisse (float_of_int n /. float_of_int images)) in
      let poids_de =
        Array.map (fun s -> lisse (Float.min 1. (Float.max 0. ((s -. (0.5 -. (fenetre /. 2.))) /. fenetre)))) temps
      in
      let dans_fenetre = List.filter (fun n -> 0. < poids_de.(n) && poids_de.(n) < 1.) (List.init images (fun n -> n + 1)) in
      let precedent = ref None and triangule = ref None in
      for n = 1 to images do
        let s = temps.(n) and poids = poids_de.(n) in
        let maillage = ref [] in
        let lignes, reduction =
          if 0. < poids && poids < 1. then begin
            let r =
              match !triangule with
              | Some r -> r
              | None ->
                  let n_b = List.nth dans_fenetre (List.length dans_fenetre - 1) + 1 in
                  let arrivee, r_b = dessin_reduit l 1 temps.(n_b) in
                  let s_a, r_a, depart = Option.get !precedent in
                  let r =
                    Raccord.raccord
                      ~positions:(fun t reduction -> Conforme.trous_ecran l ~reduction t)
                      ~clou:l.clou ~largeur:l_int ~hauteur:h_int ~s_a ~r_a ~depart ~s_b:temps.(n_b) ~r_b ~arrivee
                      ~temps:(Array.of_list (List.map (fun m -> temps.(m)) dans_fenetre))
                      ~tournants:[ l.i - 1; l.i ] ()
                  in
                  triangule := Some r;
                  r
            in
            let f = List.length (List.filter (fun m -> m < n) dans_fenetre) in
            let lignes, erreurs = Raccord.lignes ~sans_fantomes ~libre ~sans_maillage r f poids in
            List.iter (fun (lacet, e) -> anomalies := { lettre = k; image = n; detail = Printf.sprintf "lacet %d : %s" lacet e } :: !anomalies) erreurs;
            maillage := Raccord.aretes_du_maillage r f;
            (lignes, Raccord.reduction r s)
          end
          else
            let e = if poids = 0. then 0 else 1 in
            let lignes, reduction = dessin_reduit l e s in
            if poids = 0. then precedent := Some (s, reduction, lignes);
            (lignes, reduction)
        in
        let trous = Conforme.trous_ecran l ~reduction s in
        if verifie then begin
          let en_ordre = List.sort compare (Array.to_list trous) in
          if Float.abs (trous.(l.i - 1).x -. trous.(l.i).x) > 1e-6 then begin
            let lus = List.map (fun p -> Tresses.lit_mot p en_ordre) lignes in
            if not (List.mem lus mots) then anomalies := { lettre = k; image = n; detail = "mots" } :: !anomalies
          end;
          let nb = nb_croisements lignes l.clou in
          if nb > 0 then anomalies := { lettre = k; image = n; detail = Printf.sprintf "%d croisements" nb } :: !anomalies
        end;
        rendu { lignes; trous; clou = l.clou; construction = construction l ~reduction s ~poids; ab = indice_ab l ~reduction s; maillage = !maillage }
      done)
    tresse;
  List.rev !anomalies
