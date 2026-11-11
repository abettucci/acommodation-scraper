"""CLI commands for accommodation scraper."""

import sys
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import print as rprint

from .client import GooglePlacesClient
from .exporter import export_to_csv, get_summary_stats
from .models import PRO_FIELDS, ENTERPRISE_FIELDS

# Configure console for Windows compatibility
# force_terminal=True ensures colors work in Windows Terminal/PowerShell
# legacy_windows=True enables fallback for older Windows consoles (cmd.exe)
app = typer.Typer(
    name="scraper",
    help="Scraper de alojamientos usando Google Places API",
    add_completion=False,
)
console = Console(force_terminal=True, legacy_windows=True)


@app.command()
def search(
    query: str = typer.Argument(
        ...,
        help="Busqueda (ej: 'hotels', 'hostels', 'vacation rentals')",
    ),
    output: Optional[str] = typer.Option(
        None,
        "--output", "-o",
        help="Archivo CSV de salida (default: accommodations_TIMESTAMP.csv)",
    ),
    max_results: int = typer.Option(
        60,
        "--max-results", "-n",
        help="Numero maximo de resultados",
        min=1,
        max=60,
    ),
    min_rating: Optional[float] = typer.Option(
        None,
        "--min-rating", "-r",
        help="Rating minimo (1.0-5.0)",
        min=1.0,
        max=5.0,
    ),
    budget_mode: bool = typer.Option(
        False,
        "--budget-mode", "-b",
        help="Modo economico: solo campos Pro (sin reviews, rating, precio)",
    ),
    language: str = typer.Option(
        "es",
        "--language", "-l",
        help="Codigo de idioma para resultados",
    ),
    location: Optional[str] = typer.Option(
        None,
        "--location", "-L",
        help="Ciudad o direccion para centrar la busqueda (ej: 'Palermo, Buenos Aires')",
    ),
    lat: Optional[float] = typer.Option(
        None,
        "--lat",
        help="Latitud del centro de busqueda (usar con --lng y --radius)",
    ),
    lng: Optional[float] = typer.Option(
        None,
        "--lng",
        help="Longitud del centro de busqueda (usar con --lat y --radius)",
    ),
    radius: Optional[float] = typer.Option(
        None,
        "--radius", "-R",
        help="Radio de busqueda en kilometros (usar con --location o --lat/--lng)",
        min=0.1,
        max=50.0,
    ),
):
    """Buscar alojamientos y exportar a CSV.
    
    Ejemplos:
    
      scraper search "hotels" --location "Mendoza, Argentina" --radius 10
      
      scraper search "hostels" --lat -34.58 --lng -58.42 --radius 5
      
      scraper search "hotels in Buenos Aires"
    """
    
    console.print(f"\n[bold blue]Buscando:[/bold blue] {query}")
    
    if budget_mode:
        console.print("[yellow]Modo economico activado (solo campos Pro)[/yellow]")
    
    if min_rating:
        console.print(f"[dim]Filtro: rating >= {min_rating}[/dim]")
    
    # Show location info
    if location and radius:
        console.print(f"[dim]Ubicacion: {location} (radio: {radius} km)[/dim]")
    elif lat is not None and lng is not None and radius:
        console.print(f"[dim]Coordenadas: {lat}, {lng} (radio: {radius} km)[/dim]")
    
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Conectando con Google Places API...", total=None)
            
            with GooglePlacesClient() as client:
                # If location name provided, geocode it first
                resolved_lat, resolved_lng = lat, lng
                if location and radius:
                    progress.update(task, description=f"Obteniendo coordenadas de {location}...")
                    coords = client.geocode(location)
                    if coords:
                        resolved_lat, resolved_lng = coords
                        console.print(f"[dim]Coordenadas encontradas: {resolved_lat:.4f}, {resolved_lng:.4f}[/dim]")
                    else:
                        console.print(f"[yellow]No se pudo geocodificar '{location}', buscando sin restriccion de area[/yellow]")
                
                progress.update(task, description="Buscando alojamientos...")
                
                places = client.search_all(
                    query=query,
                    budget_mode=budget_mode,
                    max_results=max_results,
                    min_rating=min_rating,
                    language=language,
                    latitude=resolved_lat,
                    longitude=resolved_lng,
                    radius_km=radius,
                )
                
                progress.update(task, description="Exportando a CSV...")
        
        if not places:
            console.print("[yellow]No se encontraron resultados[/yellow]")
            raise typer.Exit(1)
        
        # Export to CSV
        output_file = export_to_csv(places, output)
        
        # Show summary
        stats = get_summary_stats(places)
        
        console.print(f"\n[bold green]Encontrados {stats['total']} alojamientos[/bold green]")
        
        if stats.get("avg_rating"):
            console.print(f"[dim]Rating promedio: {stats['avg_rating']:.1f}[/dim]")
        
        # Show types breakdown
        if stats.get("types"):
            types_str = ", ".join(f"{k}: {v}" for k, v in stats["types"].items())
            console.print(f"[dim]Tipos: {types_str}[/dim]")
        
        # Show price levels breakdown
        if stats.get("price_levels") and not budget_mode:
            prices_str = ", ".join(f"{k}: {v}" for k, v in stats["price_levels"].items())
            console.print(f"[dim]Precios: {prices_str}[/dim]")
        
        console.print(f"\n[bold]Archivo guardado:[/bold] {output_file}")
        
        # Show preview table
        _show_preview_table(places[:5])
        
    except ValueError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[bold red]Error inesperado:[/bold red] {e}")
        raise typer.Exit(1)


@app.command()
def fields():
    """Mostrar campos disponibles y sus niveles de precio."""
    
    console.print("\n[bold]Campos disponibles en Google Places API[/bold]\n")
    
    table = Table(title="Campos por Nivel de Precio")
    table.add_column("Campo", style="cyan")
    table.add_column("Descripcion", style="white")
    table.add_column("SKU", style="yellow")
    
    # Pro fields
    pro_descriptions = {
        "places.id": ("ID del lugar", "Pro"),
        "places.displayName": ("Nombre", "Pro"),
        "places.formattedAddress": ("Direccion", "Pro"),
        "places.location": ("Coordenadas (lat/lng)", "Pro"),
        "places.googleMapsUri": ("Link a Google Maps", "Pro"),
        "places.primaryType": ("Tipo de lugar", "Pro"),
    }
    
    # Enterprise fields
    enterprise_descriptions = {
        "places.rating": ("Rating (1-5)", "Enterprise"),
        "places.userRatingCount": ("Cantidad de reviews", "Enterprise"),
        "places.priceLevel": ("Nivel de precio", "Enterprise"),
        "places.internationalPhoneNumber": ("Telefono", "Enterprise"),
        "places.websiteUri": ("Sitio web", "Enterprise"),
        "places.reviews": ("Texto de reviews", "Enterprise"),
    }
    
    for field, (desc, sku) in pro_descriptions.items():
        table.add_row(field.replace("places.", ""), desc, f"[green]{sku}[/green]")
    
    for field, (desc, sku) in enterprise_descriptions.items():
        table.add_row(field.replace("places.", ""), desc, f"[yellow]{sku}[/yellow]")
    
    console.print(table)
    
    console.print("\n[bold]Costos aproximados:[/bold]")
    console.print("  [green]Pro[/green]: ~$32 USD / 1000 requests")
    console.print("  [yellow]Enterprise[/yellow]: ~$40 USD / 1000 requests")
    console.print("\n[dim]Usa --budget-mode para solo usar campos Pro[/dim]")


@app.command()
def preview(
    query: str = typer.Argument(
        ...,
        help="Busqueda para previsualizar",
    ),
    limit: int = typer.Option(
        5,
        "--limit", "-n",
        help="Numero de resultados a mostrar",
        min=1,
        max=20,
    ),
    location: Optional[str] = typer.Option(
        None,
        "--location", "-L",
        help="Ciudad o direccion para centrar la busqueda",
    ),
    radius: Optional[float] = typer.Option(
        None,
        "--radius", "-R",
        help="Radio de busqueda en kilometros",
        min=0.1,
        max=50.0,
    ),
):
    """Previsualizar resultados sin guardar a CSV."""
    
    console.print(f"\n[bold blue]Previsualizando:[/bold blue] {query}\n")
    
    try:
        with GooglePlacesClient() as client:
            # Geocode location if provided
            lat, lng = None, None
            if location and radius:
                coords = client.geocode(location)
                if coords:
                    lat, lng = coords
                    console.print(f"[dim]Buscando en {location} ({lat:.4f}, {lng:.4f}) - radio: {radius} km[/dim]\n")
            
            result = client.search(
                query=query, 
                max_results=limit,
                latitude=lat,
                longitude=lng,
                radius_km=radius,
            )
            
            if not result.places:
                console.print("[yellow]No se encontraron resultados[/yellow]")
                raise typer.Exit(1)
            
            _show_preview_table(result.places)
            
    except ValueError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(1)


@app.command()
def geocode(
    address: str = typer.Argument(
        ...,
        help="Ciudad, direccion o lugar para obtener coordenadas",
    ),
):
    """Obtener coordenadas (lat/lng) de una ciudad o direccion.
    
    Util para luego usar con --lat y --lng en el comando search.
    
    Ejemplos:
    
      scraper geocode "Palermo, Buenos Aires"
      
      scraper geocode "Mendoza, Argentina"
    """
    
    console.print(f"\n[bold blue]Geocodificando:[/bold blue] {address}\n")
    
    try:
        with GooglePlacesClient() as client:
            coords = client.geocode(address)
            
            if coords:
                lat, lng = coords
                console.print(f"[bold green]Coordenadas encontradas:[/bold green]")
                console.print(f"  Latitud:  {lat}")
                console.print(f"  Longitud: {lng}")
                console.print(f"\n[dim]Uso:[/dim]")
                console.print(f'  scraper search "hotels" --lat {lat} --lng {lng} --radius 5')
                console.print(f'\n[dim]O mas facil:[/dim]')
                console.print(f'  scraper search "hotels" --location "{address}" --radius 5')
            else:
                console.print(f"[yellow]No se encontraron coordenadas para '{address}'[/yellow]")
                raise typer.Exit(1)
                
    except ValueError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(1)


def _show_preview_table(places: list):
    """Show a preview table of places."""
    
    table = Table(title="Preview de Resultados")
    table.add_column("Nombre", style="cyan", max_width=30)
    table.add_column("Direccion", style="white", max_width=40)
    table.add_column("Rating", justify="center")
    table.add_column("Reviews", justify="right")
    table.add_column("Precio", justify="center")
    
    for place in places:
        rating = f"{place.rating:.1f}" if place.rating else "-"
        reviews = str(place.user_rating_count) if place.user_rating_count else "-"
        price = place.price_level.to_display() if place.price_level else "-"
        
        # Truncate long names and addresses
        name = place.name[:28] + "..." if len(place.name) > 30 else place.name
        address = place.address[:38] + "..." if len(place.address) > 40 else place.address
        
        table.add_row(name, address, rating, reviews, price)
    
    console.print(table)
    console.print()


if __name__ == "__main__":
    app()
