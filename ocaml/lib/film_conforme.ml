(* La boucle du film conforme (film_conforme de python/Conforme.py, sans le dessin ni le MP4, qui sont dans
   dessin/dessin.ml) et la vérification nb_croisements : étape 7d du plan OCaml. Le raccord est toujours celui par
   triangulation (le défaut du Python ; le mélange n'est pas traduit). Chaque image porte ses lignes de construction
   (l'axe et la ligne brisée L–A–B–R, avec leurs fondus pendant le raccord) ; le dessin Cairo ne les trace pas, la page web
   le fait si on le lui demande. *)

open Geometrie

type etude = {
  journal : string list;  (** le journal de l'image : ce qui est projeté, sur quoi, de quand à quand *)
  phase : int;  (** 0 : projection du départ ; 1 : raccord ; 2 : projection de l'arrivée *)
  n_a : int;  (** la dernière image du départ projeté (celle où il est figé) *)
  n_b : int;  (** la première image de l'arrivée projetée (celle où elle est figée) *)
  s_a : float;  (** le temps où le départ est figé *)
  s_b : float;  (** le temps où l'arrivée est figée *)
  plan_depart : Conforme.plan;  (** le départ au temps où il est projeté (figé à s_a pendant le raccord) *)
  plan_arrivee : Conforme.plan;
}

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
  lignes_bis : point array list;  (** mode pur : le dessin de l'arrivée (état k+1 sur L–B–A–R), en même temps que celui du départ *)
  morph : point array list;  (** mode pur : les lacets en train de se transformer de l'état k à l'état k+1 (Conforme.dessin_morph) *)
  trajets : (point * point * int) list;  (** mode pur : de chaque point du départ à son arrivée, avec son rôle (Conforme.trajets) *)
  reperes_bis : point list;  (** ses pieds *)
  reperes : point list;  (** les pieds posés sur les lignes de construction (mode pur seulement) *)
  etude : etude option;  (** le journal et les plans w, seulement si [film ~etude:true] *)
}
(* Une image du film, dans le cadre intérieur (avant le décalage de la marge). *)

type anomalie = { lettre : int; image : int; detail : string }

let lisse u = u *. u *. (3. -. (2. *. u))

(* Les lignes de construction d'une image au temps s (le [dessin_axe] du Python) : les morceaux de l'axe et A–B, puis
   L–A et B–R qui s'estompent (opacité 1 − poids) pendant que L–B et A–R apparaissent (opacité poids), poids étant la part
   du raccord : 0 sur la ligne brisée L–A–B–R de l'état k, 1 sur L–B–A–R de l'état k+1. Les segments invisibles sont omis. *)
let indice_ab l ~reduction s = List.length (fst (Conforme.aretes l ~reduction s))

let construction ?(tout = false) l ~reduction s ~poids =
  let axe, cinq = Conforme.aretes l ~reduction s in
  let avec alpha (p, q) = (p, q, alpha) in
  List.map (avec 1.) axe
  @ List.filter
      (fun (_, _, alpha) -> alpha > 0.)
      (if tout then [ avec 1. cinq.(1); avec 1. cinq.(0); avec 1. cinq.(2); avec 1. cinq.(3); avec 1. cinq.(4) ]
       else [ avec 1. cinq.(1); avec (1. -. poids) cinq.(0); avec (1. -. poids) cinq.(2); avec poids cinq.(3); avec poids cinq.(4) ])

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
  { lignes; trous = Conforme.trous_ecran l ~reduction 1.; clou = l.clou; construction = construction l ~reduction 1. ~poids:1.; ab = indice_ab l ~reduction 1.; maillage = []; reperes = []; lignes_bis = []; reperes_bis = []; trajets = []; morph = []; etude = None }


(* Le journal d'une image du film, pour l'étude de la projection : ce qui est projeté, sur quoi, de quand à quand. *)
let journal_de_l_image ~(l : Conforme.lettre) ~k ~n ~images ~n_lettres ~s ~poids ~n_a ~n_b ~s_a ~s_b ~r_d ~r_r ~phase
    ~(plan_depart : Conforme.plan) ~(plan_arrivee : Conforme.plan) =
  let z (p : Complex.t) = Printf.sprintf "(%.1f ; %.1f)" p.re p.im in
  let ligne_de (pl : Conforme.plan) =
    let noms = [| "L"; "A"; "B"; "R" |] in
    String.concat "  " (Array.to_list (Array.mapi (fun j p -> noms.(j) ^ "=" ^ z p) pl.ligne))
  in
  let antecedents (pl : Conforme.plan) = String.concat " ; " (Array.to_list (Array.map (Printf.sprintf "%.3f") pl.sommets)) in
  let compte (pl : Conforme.plan) = (List.length (List.filter (fun (_, h, _, _) -> h) pl.arcs), List.length (List.filter (fun (_, h, _, _) -> not h) pl.arcs)) in
  let lisse_borne u = lisse (Float.min 1. (Float.max 0. u)) in
  let tension = lisse_borne (poids /. 0.35) and glisse = lisse_borne ((poids -. 0.35) /. 0.3) and courbe = lisse_borne ((poids -. 0.65) /. 0.35) in
  let nb_lacets = List.length l.Conforme.etats.(0).Tresses.lacets in
  let sg = l.Conforme.sigma in
  let nom_sigma = Printf.sprintf "σ%d%s" sg.Tresses.indice (match sg.Tresses.signe with Tresses.Plus -> "" | Tresses.Moins -> "⁻¹") in
  let entete =
    [ Printf.sprintf "image %d/%d de la lettre %d/%d (%s) · s = %.4f · poids du raccord = %.4f" n images (k + 1) n_lettres nom_sigma s poids;
      Printf.sprintf "chronologie de la lettre : départ projeté aux images 0 à %d (s de 0 à %.4f) ; raccord aux images %d à %d ; arrivée projetée aux images %d à %d (s de %.4f à 1)."
        n_a s_a (n_a + 1) (n_b - 1) n_b images s_b ]
  in
  let corps =
    match phase with
    | 0 ->
        let h, b = compte plan_depart in
        [ "PHASE 1/3 : projection conforme du DÉPART (poids 0).";
          Printf.sprintf "  projeté : les %d lacets de l'état k (image clé k) : %d arc(s) du haut et %d arc(s) du bas, des demi-cercles du demi-plan w entre les antécédents de leurs pieds, plus deux descentes au clou par lacet." nb_lacets h b;
          Printf.sprintf "  sur : la ligne brisée L–A–B–R de l'état k au temps s = %.4f (y vers le haut, avant aplatissement) :" s;
          "    " ^ ligne_de plan_depart;
          Printf.sprintf "  carte de Schwarz–Christoffel : antécédents des sommets w = [%s] ; antécédent du clou %.3f %+.3fi ; réduction %.3f." (antecedents plan_depart) plan_depart.w_clou.re plan_depart.w_clou.im r_d;
          Printf.sprintf "  jusqu'à quand : jusqu'à s_a = %.4f (image %d) ; ensuite le départ reste figé et le maillage le transporte." s_a n_a ]
    | 2 ->
        let h, b = compte plan_arrivee in
        [ "PHASE 3/3 : projection conforme de l'ARRIVÉE (poids 1).";
          Printf.sprintf "  projeté : les %d lacets de l'état k+1 (image clé k+1) : %d arc(s) du haut et %d arc(s) du bas, des demi-cercles du demi-plan w entre les antécédents de leurs pieds, plus deux descentes au clou par lacet." nb_lacets h b;
          Printf.sprintf "  sur : la ligne brisée L–B–A–R de l'état k+1 au temps s = %.4f (y vers le haut, avant aplatissement) :" s;
          "    " ^ ligne_de plan_arrivee;
          Printf.sprintf "  carte de Schwarz–Christoffel : antécédents des sommets w = [%s] ; antécédent du clou %.3f %+.3fi ; réduction %.3f." (antecedents plan_arrivee) plan_arrivee.w_clou.re plan_arrivee.w_clou.im r_r;
          Printf.sprintf "  depuis quand : depuis s_b = %.4f (image %d) ; avant, l'arrivée était figée et ramenée en arrière par le maillage." s_b n_b ]
    | _ ->
        [ Printf.sprintf "PHASE 2/3 : RACCORD par triangulation mobile (images %d à %d, poids de 0 à 1)." (n_a + 1) (n_b - 1);
          Printf.sprintf "  le DÉPART, figé à s_a = %.4f (image %d, réduction %.3f), est transporté en avant par le maillage :" s_a n_a r_d;
          "    sur L–A–B–R : " ^ ligne_de plan_depart;
          Printf.sprintf "  l'ARRIVÉE, figée à s_b = %.4f (image %d, réduction %.3f), est ramenée en arrière :" s_b n_b r_r;
          "    sur L–B–A–R : " ^ ligne_de plan_arrivee;
          Printf.sprintf "  poids = %.4f : tension %.3f, glissement des pieds %.3f, courbure %.3f (phases 0 – 0,35 – 0,65 – 1)." poids tension glisse courbe;
          Printf.sprintf "  lignes de construction : L–A et B–R (départ) à l'opacité %.2f, L–B et A–R (arrivée) à l'opacité %.2f." (1. -. poids) poids;
          "  aucune projection conforme n'est calculée pendant le raccord : les plans w ci-contre sont les dessins figés." ]
  in
  entete @ corps

(* Le film : pour chaque lettre, l'état k dessiné sur L–A–B–R, puis l'état k+1 sur L–B–A–R, raccordés autour de la
   verticale par la triangulation pendant la fenêtre (part du mouvement). [rendu] est appelé avec chaque image dans
   l'ordre (la première est l'image clé de départ). Le cadre intérieur fait (hauteur − 2 marge) × (largeur − 2 marge).
   verifie : relit les mots et compte les croisements sur chaque image. detente : détend le dessin pendant le raccord
   (Detente, avec 4 poids (1 − poids)). premiere, lettres : ne calculer que l'image clé de départ (si premiere) et les lettres
   de ces indices (toutes par défaut) ; chaque lettre ne dépend que de son état de départ, son calcul est le même seule ou
   dans le film (la page en répartit les lettres sur plusieurs workers). Rend les anomalies. L'ordre des calculs est
   celui du Python, y compris celui des appels qui remplissent le cache des cartes : les derniers chiffres en
   dépendent. *)
let film ?(images = 48) ?(fenetre = 0.5) ?(verifie = false) ?(sans_fantomes = false) ?(libre = false) ?(sans_maillage = false) ?(satellites = 0) ?(pur = false) ?(etude = false) ?(detente = false) ?(premiere = true) ?lettres ~hauteur ~largeur ~marge ~rendu tresse =
  let entiers = List.map Tresses.entier_de_lettre tresse in
  let nb_trous = (match entiers with [] -> 5 | _ -> List.fold_left (fun a x -> max a (abs x)) 0 entiers) + 1 in
  let h_int = hauteur -. (2. *. marge) and l_int = largeur -. (2. *. marge) in
  let prefixe n = List.filteri (fun i _ -> i < n) tresse in
  let etat n = Tresses.etat_de_tresse ~nb_trous (prefixe n) in
  let anomalies = ref [] in
  (* première image : l'image clé, dessinée elle aussi par la carte (descentes en géodésiques) *)
  if premiere then begin
    let premiere = Conforme.lettre ~hauteur:h_int ~largeur:l_int (etat 0) (etat 1) (List.hd tresse) in
    rendu
      { lignes = Conforme.dessin premiere ~reduction:1. 0 0.; trous = Conforme.trous_ecran premiere ~reduction:1. 0.;
        clou = premiere.clou; construction = construction premiere ~reduction:1. 0. ~poids:0.; ab = indice_ab premiere ~reduction:1. 0.; maillage = []; reperes = []; lignes_bis = []; reperes_bis = []; trajets = []; morph = []; etude = None }
  end;
  List.iteri
    (fun k sigma ->
      if match lettres with None -> true | Some ls -> List.mem k ls then begin
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
        let maillage = ref [] and reperes = ref [] and lignes_bis = ref [] and reperes_bis = ref [] and trajets = ref [] and morph = ref [] in
        let lignes, reduction =
          if pur then begin
            (* projection seule, les deux phases confondues : le départ (état k sur L–A–B–R) et l'arrivée (état k+1 sur L–B–A–R)
               sont dessinés ensemble à chaque image, même là où ils n'existent pas (ligne brisée non simple) *)
            let ymin ls = List.fold_left (fun a p -> Array.fold_left (fun a q -> Float.min a q.y) a p) Float.infinity ls in
            let e0, _ = Conforme.dessin_pur l ~reduction:1. 0 s and e1, _ = Conforme.dessin_pur l ~reduction:1. 1 s in
            let y_min = Float.min (ymin e0) (ymin e1) in
            let reduction = if y_min < 10. then (l.y_axe -. 10.) /. (l.y_axe -. y_min) else 1. in
            let lignes, pieds = Conforme.dessin_pur l ~reduction 0 s and bis, pieds_bis = Conforme.dessin_pur l ~reduction 1 s in
            reperes := pieds; trajets := Conforme.trajets l ~reduction s; morph := (let m = Conforme.dessin_morph l ~reduction s s in if detente then Detente.detend m (Conforme.trous_ecran l ~reduction s) l.clou (4. *. s *. (1. -. s)) else m); lignes_bis := bis; reperes_bis := pieds_bis;
            (lignes, reduction)
          end
          else if 0. < poids && poids < 1. then begin
            let r =
              match !triangule with
              | Some r -> r
              | None ->
                  let n_b = List.nth dans_fenetre (List.length dans_fenetre - 1) + 1 in
                  let arrivee, r_b = dessin_reduit l 1 temps.(n_b) in
                  let s_a, r_a, depart = Option.get !precedent in
                  let r =
                    Raccord.raccord ~satellites
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
        (* la détente du raccord (Detente) : nulle aux bords de la fenêtre, maximale au milieu *)
        let lignes = if detente && (not pur) && 0. < poids && poids < 1. then Detente.detend lignes trous l.clou (4. *. poids *. (1. -. poids)) else lignes in
        if verifie then begin
          let en_ordre = List.sort compare (Array.to_list trous) in
          if Float.abs (trous.(l.i - 1).x -. trous.(l.i).x) > 1e-6 then begin
            let lus = List.map (fun p -> Tresses.lit_mot p en_ordre) lignes in
            if not (List.mem lus mots) then anomalies := { lettre = k; image = n; detail = "mots" } :: !anomalies
          end;
          let nb = nb_croisements lignes l.clou in
          if nb > 0 then anomalies := { lettre = k; image = n; detail = Printf.sprintf "%d croisements" nb } :: !anomalies
        end;
        let etude_de_l_image =
          if not etude then None
          else begin
            (* l'étude : travaille sur une copie de la lettre (et de son cache), le film n'en est pas modifié *)
            let le = { l with Conforme.cache = Hashtbl.copy l.Conforme.cache } in
            let n_a = List.hd dans_fenetre - 1 and n_b = List.nth dans_fenetre (List.length dans_fenetre - 1) + 1 in
            let s_a = temps.(n_a) and s_b = temps.(n_b) in
            let s_d = if n <= n_a then s else s_a and s_r = if n >= n_b then s else s_b in
            let r_d = snd (dessin_reduit le 0 s_d) and r_r = snd (dessin_reduit le 1 s_r) in
            let plan_depart = Conforme.plan_w le ~reduction:r_d 0 s_d and plan_arrivee = Conforme.plan_w le ~reduction:r_r 1 s_r in
            let phase = if n <= n_a then 0 else if n >= n_b then 2 else 1 in
            let journal =
              journal_de_l_image ~l ~k ~n ~images ~n_lettres:(List.length tresse) ~s ~poids ~n_a ~n_b ~s_a ~s_b ~r_d ~r_r ~phase ~plan_depart
                ~plan_arrivee
            in
            Some { journal; phase; n_a; n_b; s_a; s_b; plan_depart; plan_arrivee }
          end
        in
        rendu { lignes; trous; clou = l.clou; construction = construction ~tout:pur l ~reduction s ~poids; ab = indice_ab l ~reduction s; maillage = !maillage; reperes = !reperes; lignes_bis = !lignes_bis; reperes_bis = !reperes_bis; trajets = !trajets; morph = !morph;
                etude = etude_de_l_image }
      done
      end)
    tresse;
  List.rev !anomalies
