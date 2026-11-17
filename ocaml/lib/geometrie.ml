(* Points et vecteurs du plan, communs à tous les modules. Le Python se sert des tableaux numpy (p - q, a * u,
   u @ v) ; OCaml n'a pas de surcharge d'opérateurs : les opérations sur les points ont leurs propres symboles,
   terminés par « : ». *)

type point = { x : float; y : float }

let ( +: ) p q = { x = p.x +. q.x; y = p.y +. q.y }
let ( -: ) p q = { x = p.x -. q.x; y = p.y -. q.y }
let ( *: ) a p = { x = a *. p.x; y = a *. p.y }
let oppose p = { x = -.p.x; y = -.p.y }

(* Produit vectoriel (déterminant) : > 0 si on tourne dans le sens direct de u vers v. *)
let croix u v = (u.x *. v.y) -. (u.y *. v.x)

(* Produit scalaire, le u @ v du Python. *)
let scalaire u v = (u.x *. v.x) +. (u.y *. v.y)

(* Longueur, le math.hypot du Python. *)
let norme u = Float.hypot u.x u.y
