from datetime import date

from django.core.management.base import BaseCommand
from django.db import transaction

from media.models import Credito, Genero, Media, Persona


MEDIA_DATA = [
    {
        "titulo": "Cadena perpetua",
        "titulo_original": "The Shawshank Redemption",
        "tipo": Media.Tipo.PELICULA,
        "fecha_estreno": date(1994, 9, 23),
        "duracion": 142,
        "generos": ("Drama", "Crimen"),
        "directores": ("Frank Darabont",),
        "actores": ("Tim Robbins", "Morgan Freeman", "Bob Gunton"),
    },
    {
        "titulo": "El padrino",
        "titulo_original": "The Godfather",
        "tipo": Media.Tipo.PELICULA,
        "fecha_estreno": date(1972, 3, 24),
        "duracion": 175,
        "generos": ("Crimen", "Drama"),
        "directores": ("Francis Ford Coppola",),
        "actores": ("Marlon Brando", "Al Pacino", "James Caan"),
    },
    {
        "titulo": "El caballero oscuro",
        "titulo_original": "The Dark Knight",
        "tipo": Media.Tipo.PELICULA,
        "fecha_estreno": date(2008, 7, 18),
        "duracion": 152,
        "generos": ("Acción", "Crimen"),
        "directores": ("Christopher Nolan",),
        "actores": ("Christian Bale", "Heath Ledger", "Aaron Eckhart"),
    },
    {
        "titulo": "Pulp Fiction",
        "titulo_original": "Pulp Fiction",
        "tipo": Media.Tipo.PELICULA,
        "fecha_estreno": date(1994, 10, 14),
        "duracion": 154,
        "generos": ("Crimen", "Drama"),
        "directores": ("Quentin Tarantino",),
        "actores": ("John Travolta", "Samuel L. Jackson", "Uma Thurman"),
    },
    {
        "titulo": "El viaje de Chihiro",
        "titulo_original": "Sen to Chihiro no Kamikakushi",
        "tipo": Media.Tipo.ANIME,
        "fecha_estreno": date(2001, 7, 20),
        "duracion": 125,
        "generos": ("Anime", "Fantasía", "Aventura"),
        "directores": ("Hayao Miyazaki",),
        "actores": ("Rumi Hiiragi", "Miyu Irino", "Mari Natsuki"),
    },
    {
        "titulo": "Parásitos",
        "titulo_original": "Gisaengchung",
        "tipo": Media.Tipo.PELICULA,
        "fecha_estreno": date(2019, 5, 30),
        "duracion": 132,
        "generos": ("Drama", "Suspenso"),
        "directores": ("Bong Joon-ho",),
        "actores": ("Song Kang-ho", "Lee Sun-kyun", "Cho Yeo-jeong"),
    },
    {
        "titulo": "El origen",
        "titulo_original": "Inception",
        "tipo": Media.Tipo.PELICULA,
        "fecha_estreno": date(2010, 7, 16),
        "duracion": 148,
        "generos": ("Ciencia ficción", "Acción"),
        "directores": ("Christopher Nolan",),
        "actores": ("Leonardo DiCaprio", "Joseph Gordon-Levitt", "Elliot Page"),
    },
    {
        "titulo": "Coco",
        "titulo_original": "Coco",
        "tipo": Media.Tipo.PELICULA,
        "fecha_estreno": date(2017, 11, 22),
        "duracion": 105,
        "generos": ("Animación", "Aventura", "Familia"),
        "directores": ("Lee Unkrich",),
        "actores": ("Anthony Gonzalez", "Gael García Bernal", "Benjamin Bratt"),
    },
    {
        "titulo": "Interestelar",
        "titulo_original": "Interstellar",
        "tipo": Media.Tipo.PELICULA,
        "fecha_estreno": date(2014, 11, 7),
        "duracion": 169,
        "generos": ("Ciencia ficción", "Drama", "Aventura"),
        "directores": ("Christopher Nolan",),
        "actores": ("Matthew McConaughey", "Anne Hathaway", "Jessica Chastain"),
    },
    {
        "titulo": "Parque Jurásico",
        "titulo_original": "Jurassic Park",
        "tipo": Media.Tipo.PELICULA,
        "fecha_estreno": date(1993, 6, 11),
        "duracion": 127,
        "generos": ("Aventura", "Ciencia ficción"),
        "directores": ("Steven Spielberg",),
        "actores": ("Sam Neill", "Laura Dern", "Jeff Goldblum"),
    },
    {
        "titulo": "Matrix",
        "titulo_original": "The Matrix",
        "tipo": Media.Tipo.PELICULA,
        "fecha_estreno": date(1999, 3, 31),
        "duracion": 136,
        "generos": ("Ciencia ficción", "Acción"),
        "directores": ("Lana Wachowski", "Lilly Wachowski"),
        "actores": ("Keanu Reeves", "Laurence Fishburne", "Carrie-Anne Moss"),
    },
    {
        "titulo": "La comunidad del anillo",
        "titulo_original": "The Lord of the Rings: The Fellowship of the Ring",
        "tipo": Media.Tipo.PELICULA,
        "fecha_estreno": date(2001, 12, 19),
        "duracion": 178,
        "generos": ("Fantasía", "Aventura"),
        "directores": ("Peter Jackson",),
        "actores": ("Elijah Wood", "Ian McKellen", "Viggo Mortensen"),
    },
    {
        "titulo": "Titanic",
        "titulo_original": "Titanic",
        "tipo": Media.Tipo.PELICULA,
        "fecha_estreno": date(1997, 12, 19),
        "duracion": 195,
        "generos": ("Drama", "Romance"),
        "directores": ("James Cameron",),
        "actores": ("Leonardo DiCaprio", "Kate Winslet", "Billy Zane"),
    },
    {
        "titulo": "Amélie",
        "titulo_original": "Le Fabuleux Destin d'Amélie Poulain",
        "tipo": Media.Tipo.PELICULA,
        "fecha_estreno": date(2001, 4, 25),
        "duracion": 122,
        "generos": ("Romance", "Comedia"),
        "directores": ("Jean-Pierre Jeunet",),
        "actores": ("Audrey Tautou", "Mathieu Kassovitz", "Rufus"),
    },
    {
        "titulo": "Whiplash",
        "titulo_original": "Whiplash",
        "tipo": Media.Tipo.PELICULA,
        "fecha_estreno": date(2014, 10, 10),
        "duracion": 107,
        "generos": ("Drama", "Música"),
        "directores": ("Damien Chazelle",),
        "actores": ("Miles Teller", "J. K. Simmons", "Paul Reiser"),
    },
    {
        "titulo": "Déjame salir",
        "titulo_original": "Get Out",
        "tipo": Media.Tipo.PELICULA,
        "fecha_estreno": date(2017, 2, 24),
        "duracion": 104,
        "generos": ("Terror", "Suspenso"),
        "directores": ("Jordan Peele",),
        "actores": ("Daniel Kaluuya", "Allison Williams", "Bradley Whitford"),
    },
    {
        "titulo": "La La Land",
        "titulo_original": "La La Land",
        "tipo": Media.Tipo.PELICULA,
        "fecha_estreno": date(2016, 12, 9),
        "duracion": 128,
        "generos": ("Romance", "Música", "Drama"),
        "directores": ("Damien Chazelle",),
        "actores": ("Ryan Gosling", "Emma Stone", "John Legend"),
    },
    {
        "titulo": "Toy Story",
        "titulo_original": "Toy Story",
        "tipo": Media.Tipo.PELICULA,
        "fecha_estreno": date(1995, 11, 22),
        "duracion": 81,
        "generos": ("Animación", "Aventura", "Comedia"),
        "directores": ("John Lasseter",),
        "actores": ("Tom Hanks", "Tim Allen", "Don Rickles"),
    },
    {
        "titulo": "Todo a la vez en todas partes",
        "titulo_original": "Everything Everywhere All at Once",
        "tipo": Media.Tipo.PELICULA,
        "fecha_estreno": date(2022, 3, 25),
        "duracion": 139,
        "generos": ("Ciencia ficción", "Aventura", "Comedia"),
        "directores": ("Daniel Kwan", "Daniel Scheinert"),
        "actores": ("Michelle Yeoh", "Stephanie Hsu", "Ke Huy Quan"),
    },
    {
        "titulo": "El gran hotel Budapest",
        "titulo_original": "The Grand Budapest Hotel",
        "tipo": Media.Tipo.PELICULA,
        "fecha_estreno": date(2014, 3, 28),
        "duracion": 99,
        "generos": ("Comedia", "Aventura"),
        "directores": ("Wes Anderson",),
        "actores": ("Ralph Fiennes", "Tony Revolori", "Saoirse Ronan"),
    },
    {
        "titulo": "Up: Una aventura de altura",
        "titulo_original": "Up",
        "tipo": Media.Tipo.PELICULA,
        "fecha_estreno": date(2009, 5, 29),
        "duracion": 96,
        "generos": ("Animación", "Aventura", "Familia"),
        "directores": ("Pete Docter",),
        "actores": ("Ed Asner", "Jordan Nagai", "Bob Peterson"),
    },
    {
        "titulo": "Dune",
        "titulo_original": "Dune",
        "tipo": Media.Tipo.PELICULA,
        "fecha_estreno": date(2021, 10, 22),
        "duracion": 155,
        "generos": ("Ciencia ficción", "Aventura", "Drama"),
        "directores": ("Denis Villeneuve",),
        "actores": ("Timothée Chalamet", "Rebecca Ferguson", "Oscar Isaac"),
    },
    {
        "titulo": "El show de Truman",
        "titulo_original": "The Truman Show",
        "tipo": Media.Tipo.PELICULA,
        "fecha_estreno": date(1998, 6, 5),
        "duracion": 103,
        "generos": ("Drama", "Comedia"),
        "directores": ("Peter Weir",),
        "actores": ("Jim Carrey", "Ed Harris", "Laura Linney"),
    },
    {
        "titulo": "Shrek",
        "titulo_original": "Shrek",
        "tipo": Media.Tipo.PELICULA,
        "fecha_estreno": date(2001, 4, 22),
        "duracion": 90,
        "generos": ("Animación", "Comedia", "Fantasía"),
        "directores": ("Andrew Adamson",),
        "actores": ("Mike Myers", "Eddie Murphy", "Cameron Diaz"),
    },
    {
        "titulo": "El silencio de los inocentes",
        "titulo_original": "The Silence of the Lambs",
        "tipo": Media.Tipo.PELICULA,
        "fecha_estreno": date(1991, 2, 14),
        "duracion": 118,
        "generos": ("Suspenso", "Crimen", "Terror"),
        "directores": ("Jonathan Demme",),
        "actores": ("Jodie Foster", "Anthony Hopkins", "Scott Glenn"),
    },
    {
        "titulo": "Blade Runner",
        "titulo_original": "Blade Runner",
        "tipo": Media.Tipo.PELICULA,
        "fecha_estreno": date(1982, 6, 25),
        "duracion": 117,
        "generos": ("Ciencia ficción", "Suspenso"),
        "directores": ("Ridley Scott",),
        "actores": ("Harrison Ford", "Rutger Hauer", "Sean Young"),
    },
    {
        "titulo": "Perfect Blue",
        "titulo_original": "Perfect Blue",
        "tipo": Media.Tipo.ANIME,
        "fecha_estreno": date(1998, 2, 28),
        "duracion": 81,
        "generos": ("Anime", "Suspenso", "Drama"),
        "directores": ("Satoshi Kon",),
        "actores": ("Junko Iwao", "Rica Matsumoto", "Shinpachi Tsuji"),
    },
    {
        "titulo": "Spider-Man: Un nuevo universo",
        "titulo_original": "Spider-Man: Into the Spider-Verse",
        "tipo": Media.Tipo.PELICULA,
        "fecha_estreno": date(2018, 12, 14),
        "duracion": 117,
        "generos": ("Animación", "Acción", "Aventura"),
        "directores": ("Bob Persichetti", "Peter Ramsey", "Rodney Rothman"),
        "actores": ("Shameik Moore", "Jake Johnson", "Hailee Steinfeld"),
    },
    {
        "titulo": "Breaking Bad",
        "titulo_original": "Breaking Bad",
        "tipo": Media.Tipo.SERIE,
        "fecha_estreno": date(2008, 1, 20),
        "duracion": 47,
        "generos": ("Drama", "Crimen", "Suspenso"),
        "directores": ("Vince Gilligan",),
        "actores": ("Bryan Cranston", "Aaron Paul", "Anna Gunn"),
    },
    {
        "titulo": "Juego de tronos",
        "titulo_original": "Game of Thrones",
        "tipo": Media.Tipo.SERIE,
        "fecha_estreno": date(2011, 4, 17),
        "duracion": 57,
        "generos": ("Fantasía", "Drama", "Aventura"),
        "directores": ("Tim Van Patten",),
        "actores": ("Emilia Clarke", "Kit Harington", "Peter Dinklage"),
    },
    {
        "titulo": "The Office",
        "titulo_original": "The Office",
        "tipo": Media.Tipo.SERIE,
        "fecha_estreno": date(2005, 3, 24),
        "duracion": 22,
        "generos": ("Comedia",),
        "directores": ("Ken Kwapis",),
        "actores": ("Steve Carell", "John Krasinski", "Jenna Fischer"),
    },
    {
        "titulo": "Stranger Things",
        "titulo_original": "Stranger Things",
        "tipo": Media.Tipo.SERIE,
        "fecha_estreno": date(2016, 7, 15),
        "duracion": 51,
        "generos": ("Ciencia ficción", "Terror", "Drama"),
        "directores": ("Matt Duffer", "Ross Duffer"),
        "actores": ("Millie Bobby Brown", "Finn Wolfhard", "Winona Ryder"),
    },
    {
        "titulo": "The Last of Us",
        "titulo_original": "The Last of Us",
        "tipo": Media.Tipo.SERIE,
        "fecha_estreno": date(2023, 1, 15),
        "duracion": 50,
        "generos": ("Drama", "Acción", "Aventura"),
        "directores": ("Kantemir Balagov",),
        "actores": ("Pedro Pascal", "Bella Ramsey", "Anna Torv"),
    },
    {
        "titulo": "Fullmetal Alchemist: Brotherhood",
        "titulo_original": "Hagane no Renkinjutsushi",
        "tipo": Media.Tipo.ANIME,
        "fecha_estreno": date(2009, 4, 5),
        "duracion": 24,
        "generos": ("Anime", "Acción", "Fantasía"),
        "directores": ("Yasuhiro Irie",),
        "actores": ("Romi Park", "Rie Kugimiya", "Shinichiro Miki"),
    },
    {
        "titulo": "Death Note",
        "titulo_original": "Desu Noto",
        "tipo": Media.Tipo.ANIME,
        "fecha_estreno": date(2006, 10, 4),
        "duracion": 23,
        "generos": ("Anime", "Suspenso", "Crimen"),
        "directores": ("Tetsuro Araki",),
        "actores": ("Mamoru Miyano", "Kappei Yamaguchi", "Shido Nakamura"),
    },
    {
        "titulo": "Cowboy Bebop",
        "titulo_original": "Kaubōi Bibappu",
        "tipo": Media.Tipo.ANIME,
        "fecha_estreno": date(1998, 4, 3),
        "duracion": 24,
        "generos": ("Anime", "Ciencia ficción", "Aventura"),
        "directores": ("Shinichiro Watanabe",),
        "actores": ("Koichi Yamadera", "Unsho Ishizuka", "Megumi Hayashibara"),
    },
    {
        "titulo": "Ataque a los titanes",
        "titulo_original": "Shingeki no Kyojin",
        "tipo": Media.Tipo.ANIME,
        "fecha_estreno": date(2013, 4, 7),
        "duracion": 24,
        "generos": ("Anime", "Acción", "Drama"),
        "directores": ("Tetsuro Araki",),
        "actores": ("Yuki Kaji", "Yui Ishikawa", "Marina Inoue"),
    },
]


class Command(BaseCommand):
    help = "Carga un catálogo inicial de películas, series y anime."

    def handle(self, *args, **options):
        media_created = 0
        media_updated = 0

        with transaction.atomic():
            for item in MEDIA_DATA:
                defaults = {
                    "titulo_original": item["titulo_original"],
                    "tipo": item["tipo"],
                    "fecha_estreno": item["fecha_estreno"],
                    "duracion": item["duracion"],
                    "estado": Media.Estado.FUERA_CARTELERA,
                }
                media, created = Media.objects.update_or_create(
                    titulo=item["titulo"], defaults=defaults
                )
                media_created += created
                media_updated += not created

                generos = [
                    Genero.objects.get_or_create(nombre=nombre)[0]
                    for nombre in item["generos"]
                ]
                media.generos.set(generos)

                creditos = [
                    (nombre, Credito.Rol.DIRECTOR)
                    for nombre in item["directores"]
                ] + [(nombre, Credito.Rol.ACTOR) for nombre in item["actores"]]

                for nombre, rol in creditos:
                    persona, _ = Persona.objects.get_or_create(nombre=nombre)
                    Credito.objects.get_or_create(
                        media=media,
                        persona=persona,
                        rol=rol,
                    )

        self.stdout.write(
            self.style.SUCCESS(
                f"Catálogo listo: {len(MEDIA_DATA)} fichas; "
                f"{media_created} nuevas y {media_updated} actualizadas."
            )
        )