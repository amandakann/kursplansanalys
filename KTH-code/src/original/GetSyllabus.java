package KTHoriginal;

import java.io.IOException;
import java.net.MalformedURLException;
import java.net.URL;
import java.net.URLEncoder;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;
import java.util.stream.IntStream;
import java.util.stream.Stream;

import org.apache.commons.lang3.StringEscapeUtils;
import org.jsoup.HttpStatusException;
import org.jsoup.Jsoup;
import org.jsoup.nodes.Document;
import org.jsoup.nodes.Element;
import org.jsoup.nodes.Node;
import org.jsoup.select.Elements;


/**
 * A syllabus classifier implemented as part of my thesis
 * "Analyzing KTH's course syllabuses from a pedagogical perspective".
 * The CSV output from this class is used as input to ResultsCreator.java.
 * 
 * @author Joakim Lindberg, modified by Viggo Kann
 * @version 2024-03-01
 */
public class GetSyllabus {
    static private int debug = 0;
    static boolean syllabusOutput = false;
    
    // Flag for enabling search for SPECIFIC keywords 
    // If set to true, a CSV file called "specific_keywords.csv" will be created.
    static final private boolean FIND_SPECIFIC_KEYWORDS = true;

    // SPECIFIC keywords are either ECE keywords (research, labor market, innovation), SUSTAINABILITY keywords or OTHER keywords
    // If FIND_SPECIFIC_KEYWORDS and the flag below are set to true, output these keywords to specific_keywords.csv
    static final private boolean FIND_ECE_KEYWORDS = false; //false;
    static final private boolean FIND_SUSTAINABILITY_KEYWORDS = false; //true;
    static final private boolean FIND_OTHER_KEYWORDS = true; //true;

        // If set to true, spelling errors in the course sylabus are corrected
	static final private boolean correctSpelling = true;

        // Character used to represent a list item.
        static final private String LISTCHAR = "¢";

	// Paths to the files containing verbs in Bloom's taxonomy.
    //	static final private String[] BLOOM_VERBS_PATHS = {"data/blooms_original.txt", "data/blooms_added.txt"};
    	static final private String[] BLOOM_VERBS_PATHS = {"data/bloom_revised_all_words.txt"};
	
	// Maps a verb to its corresponding class in Bloom's taxonomy.
	HashMap<Integer, HashMap<List<String>, Integer>> verbToBloom = new HashMap<>();
	
	// The number of classes in Bloom's taxonomy.
	static final private int N_BLOOM_CLASSES = 6;
	
	// Constants for language identification.
	static final int LANG_SWEDISH = 0;
	static final int LANG_ENGLISH = 1;
	
	// Words commonly used in ILO headers.
	static final private List<String> ILOHeaderWords = Arrays.asList(
			"genomgången", "avslutad", "fullgjord", "avklarad", "avslutad", "genomförd", "fullbordande",
			"godkänd", "slutförd", "deltagare", "kursdeltagare", "student", "teknolog", "du");

	// Default course semester.
        static final private String defaultSemester = "2023:2";
    
	// Constants for row classification.
	static final private int ROW_OTHER = 0;
	static final private int ROW_ILO = 1;
	static final private int ROW_ILO_LIST_HEADER = 2;
	static final private int ROW_HIGHER_GRADE_HEADER = 3;
	static final private int ROW_PURPOSE_HEADER = 4;
	static final private int ROW_HF_LEVELS_HEADER = 5;
	static final private int ROW_COURSE_DESCRIPTION = 6;
	static final private int ROW_COMBO_ILO_HEADER = 7;
	static final private int ROW_HIGHER_GRADE_ILO = 8;
	static final private int ROW_PURPOSE_ILO = 9;
	static final private int ROW_ILO_NO_VERB = 10;
	
	// The base URL to the KTH course- and program information API.
	static final private String BASE_API_URL = "https://api.kth.se/api/kopps/v1/";
	
	// The number of trigrams to read from file.
	static final private int TRIGRAMS_LIMIT = 1000;
	
	// Used for storing the top n-grams.
	private ArrayList<String> sweTopTrigrams = new ArrayList<>();
	private ArrayList<String> engTopTrigrams = new ArrayList<>();
	
	// Contains the course subjects (main fields of study) for each course.
	private HashMap<String, ArrayList<String>> courseSubjects = new HashMap<>();
	
	// The Granska tag numbers corresponding to verbs.
	final private List<Integer> VERB_TAGS_GRANSKA = Arrays.asList(
			15, 21, 30, 39, 47, 54, 59, 62, 63, 64,
			74, 77, 79, 82, 83, 87, 94, 98, 108, 112,
			114, 117, 125, 127, 132, 134, 137, 146);
	
	// Used for building the output strings. 
	private StringBuilder outputCSV = new StringBuilder();
	private StringBuilder outputSPECIFIC;
	
	// Contain all words and verbs in the syllabus separated by which row (inner list) it occurred in. 
	private List<List<String>> syllabusWords;
	private List<List<String>> syllabusRawWords;
	
	// Sets of all words and verbs used in all syllabuses.
	private Set<String> allWordsTotal = new HashSet<>();
	private Set<String> allVerbsTotal = new HashSet<>();
	
	// Research keywords.
	static final private Set<String> researchKeywords = Stream.of(
			"forskning", "forskningsprojekt", "forskningsmetod", "datainsamlingsmetod", "vetenskaplig")
            .collect(Collectors.toCollection(HashSet::new));
	
	// Labor market keywords.
	static final private Set<String> laborMarketKeywords = Stream.of(
			"industri", "arbetsliv", "företag", "organisation", "utvecklingsprojekt", "studiebesök",
			"förändringsprojekt", "verklig", "roll", "yrkesroll", "ingenjörsarbete", "yrkesverksam")
			.collect(Collectors.toCollection(HashSet::new));
	
	// Innovation keywords.
	static final private Set<String> innovationKeywords = Stream.of(
			"innovation", "entreprenör", "utmaning")
            .collect(Collectors.toCollection(HashSet::new));
	
	// Other keywords.
	static final private Set<String> otherKeywords = Stream.of(
								   "samordnare", "funktionsnedsättning", "Funka", "anpassad", "omexamination", "särskilda", "hederskodex", "förstagångsregistrerad")
            .collect(Collectors.toCollection(HashSet::new));
	
	// Sustainability keywords.
	static final private Set<String> sustainabilityKeywords = Stream.of(
"fattigdom", "inkomstfördelning", "förmögenhetsfördelning", "socioekonomisk", "jordbruk",
// "mat",
"näring", "hälsa", "välbefinnande",
// "utbild",
// "inkludera",
"rättvis", "kön", "kvinnor", "jämställd", "flick", "tjej", "queer", "vatten", "sanitet",
"energi", "förny", "vind",
// "sol",
"jordvärme", "vattenkraft", "sysselsättning", "ekonomisk tillväxt", "hållbar utveckling", "arbetskraft",
"arbetare",
// "lön",
"infrastruktur", "innovation",
// "industri",
"byggnader", "handel", "ojämlikhet", "finansmarknad", "beskattning",
"städer", "urban", "resilien","landsbygd", "konsumtion", "produktion", "avfall", "naturresurser", "återvinning", "industriell ekologi",
"hållbar design", "klimat", "växthusgas", "miljö", "global uppvärmning", "väder",
// "hav",
"marin", "vatten", "förorena", "bevara", "fisk",
"skog", "biologisk mångfald", "ekologi", "förorena", "bevara", "markanvändning", "institution", "rättvisa", "styrelseformer", "fred",
"rättigheter"
			)
            .collect(Collectors.toCollection(HashSet::new));
	
	// Ethics keywords.
	static final private Set<String> ethicsKeywords = Stream.of(
			"heder", "kodex", "fusk", "plagi")
            .collect(Collectors.toCollection(HashSet::new));
	
	// Used to print a status message containing how many courses have been handled so far.
	private int nHandled = 0;

	
	/**
	 * Accesses and classifies all syllabuses and outputs the results.
	 * 
	 * @throws IOException
	 * @throws InterruptedException
	 */
    public GetSyllabus(boolean handleAllCourses, String courseCode, String courseSemester, boolean fullYear, String outputFileName)
			throws IOException, InterruptedException {
                if (courseSemester == null || courseSemester.equals("")) courseSemester = defaultSemester;
		
		// Read the top n-grams (down to the given limit) with the highest frequency from file.
		Files.lines(Paths.get("data/swedish_trigrams.txt")).limit(TRIGRAMS_LIMIT).forEach(s -> sweTopTrigrams.add(s));
		Files.lines(Paths.get("data/english_trigrams.txt")).limit(TRIGRAMS_LIMIT).forEach(s -> engTopTrigrams.add(s));
		
		// Read the main fields of study (course subjects) from file.
		Files.lines(Paths.get("data/course_subjects.csv")).forEach(line -> {
			String[] tokens = line.split(";");
			if (courseSubjects.containsKey(tokens[0])) {
				courseSubjects.get(tokens[0]).add(tokens[1]);
			} else {
				ArrayList<String> list = new ArrayList<>();
				list.add(tokens[1]);
				courseSubjects.put(tokens[0], list);
			}
		});

		// Load the verbs in Bloom's taxonomy from file.
		loadBloomVerbs();
		
		// Write the CSV header.
		outputCSV.append("code;syll_lang_swe;syll_lang_eng;content;goals_swe;goals_eng;eligibility;literature;exam_comments;req_for_grade;"
				+ "valid_from;equipment;instruction_lang;cycle;credits;title_swe;title_eng;grade_scale;"
				+ "department;examiner;n_exam_modules;n_course_subjects;ethics_keywords;"
				+ "n_rows;n_ilos;n_higher_grade_ilos;n_purpose_ilos;bloom_knowledge;bloom_comprehension;"
				+ "bloom_application;bloom_analysis;bloom_evaluation;bloom_synthesis;total_highest_bloom\n");
		
		// If the flag for finding SPECIFIC keywords is set,
		// initialize the StringBuilder for the output.
		if (FIND_SPECIFIC_KEYWORDS) {
			outputSPECIFIC = new StringBuilder();
			outputSPECIFIC.append("course");
			if (FIND_ECE_KEYWORDS) 
			    outputSPECIFIC.append(";research;laborMarket;innovation");
			if (FIND_SUSTAINABILITY_KEYWORDS) 
			    outputSPECIFIC.append(";sustainability");

			if (FIND_OTHER_KEYWORDS) 
			    outputSPECIFIC.append(";other_keywords");
outputSPECIFIC.append("\n");
		}
		
		// Either handle all courses or just one specific course. 
		if (handleAllCourses) {
			
			HashMap<String, String> courses = new HashMap<>();
			if (fullYear) {
			    String secondSemester = courseSemester.split(":",0)[1].equals("1") ? courseSemester.split(":",0)[0]+":2" :
				Integer.toString(Integer.parseInt(courseSemester.split(":",0)[0])+1)+":1";
			    System.out.println("Finding all course offerings during the semesters "+courseSemester+" and "+secondSemester);
			    GetAllCoursesFromSemester(courses, courseSemester);
			    GetAllCoursesFromSemester(courses, secondSemester);
			} else {
			    System.out.println("Finding all course offerings during the semester "+courseSemester);
			    GetAllCoursesFromSemester(courses, courseSemester);
			}
			
			// Handle all courses.
			courses.entrySet().stream().forEach(entry -> {
				try {
					
					// Handle the given course and increase the counter.
					handleCourse(entry.getKey(), entry.getValue());
					nHandled++;
					
					// Print how many courses have been handled so far.
					if (debug != 10 && debug != 20)
					System.err.print("\rHandled courses: " + nHandled + " (out of " + courses.size() + ")");
				} catch (Exception e) {
					System.out.println("Could not handle " + entry.getKey() + " (semester " + entry.getValue() + ")!");
					if (debug >= 1000000) {
					    e.printStackTrace();
					    System.exit(1);
					}
				}
			});
			System.out.println();
		} else {
			handleCourse(courseCode, courseSemester);
		}

		// Write the results to file.
		Files.write(Paths.get(outputFileName), outputCSV.toString().getBytes());
		
		// If the flag for finding SPECIFIC keywords is set,
		// write the found keywords to file.
		if (FIND_SPECIFIC_KEYWORDS) {
			Files.write(Paths.get("specific_keywords.csv"), outputSPECIFIC.toString().getBytes());
		}
	}


	/**
	 * Download and parse all course rounds for a semester.
	 * 
	 * @param courses A hashmap where the courses are put.
	 * @param semester The semester which the course is given in.
	 * @throws IOException 
	 */
    private void GetAllCoursesFromSemester(HashMap<String, String> courses, String semester) throws IOException{
	Elements courseOfferings = Jsoup.connect(BASE_API_URL + "courseRounds/" + semester).get().select("courseRound");
			
	// Add the course codes to a set to remove duplicates.
	for (Element round : courseOfferings)
	    courses.put(round.attr("courseCode"), semester);
    }
    
	
	/**
	 * Download the syllabus for the given course and process it.
	 * 
	 * @param courseCode The course code.
	 * @param semester The semester which the course is given in.
	 * @throws InterruptedException 
	 */
	private void handleCourse(String courseCode, String semester) throws MalformedURLException, IOException, InterruptedException {
		syllabusWords = new ArrayList<>();
		syllabusRawWords = new ArrayList<>();
		
		// Connect to the KTH API and fetch the course plan.
		Document origPlan = Jsoup.connect(BASE_API_URL + "course/" + courseCode + "/plan/" + semester).get();
		
		// Try fetching the first course round. If no round with ID 1 exists,
		// increment the round ID and retry until it works (up to round ID 10).
		Document origRound = null;
		int roundId = 1;
		while (origRound == null) {
			try {
				origRound = Jsoup.connect(BASE_API_URL + "course/" + courseCode + "/round/" + semester + "/" + roundId).get();
			} catch (HttpStatusException e) {
				if (roundId < 10) {
					roundId++;
				} else {
				    System.err.println(courseCode + " (" + semester + "): Failed fetching course offering!");
				    return;
				}
			}
		}
		
		// Fetch the overall course information.
		Document origCourse = Jsoup.connect(BASE_API_URL + "course/" + courseCode).get();
		
		// Try fetching the examination set. If it does not exist, create a
		// dummy examination set containing two nested elements without text contents
		// to make processing simpler later.
		Document origExaminationSet;
		try {
		    //origExaminationSet = Jsoup.connect(BASE_API_URL + "course/" + courseCode + "/examination-set").get();
			origExaminationSet = Jsoup.connect(BASE_API_URL + "course/" + courseCode + "/examination-set/" + semester).get();
		} catch (HttpStatusException e) {
			origExaminationSet = new Document(courseCode);
			origExaminationSet.append("<xxx_empty><yyy_empty></yyy_empty></xxx_empty>");
		}
		
		// Unescape entities and parse the XMLs into jsoup elements.
		Element plan = Jsoup.parse(unescapeEntities(origPlan)).body().child(0);
		Element round = Jsoup.parse(unescapeEntities(origRound)).body().child(0);
		Element course = Jsoup.parse(unescapeEntities(origCourse)).body().child(0);
		Element examinationSet = Jsoup.parse(unescapeEntities(origExaminationSet)).body().child(0);
		
		// Used for printing the CSV results.
		StringBuilder sbCSV = new StringBuilder();
		
		// Variables for keeping track of words regarding Bloom's taxonomy.
		int[][] bloomsDistribution = new int[0][0];
		int[] highestBloomClass = new int[0];
		int[] bloomFrequency = new int[N_BLOOM_CLASSES];
		
		// Keeps track of which type each row has.
		int[] rowTypes;
		
		// Counters for the different ILO types.
		int nNormalILOs = 0;
		int nHigherGradeILOs = 0;
		int nPurposeILOs = 0;

		if (debug == 24 && 
		    contentExists(plan, "eligibility[xml:lang=sv]") > 0) 
		    System.out.println(courseCode+": " + contentValue(plan, "eligibility[xml:lang=sv]"));
		    
		if (debug == 25 && (courseCode.startsWith("D") || courseCode.startsWith("I") || courseCode.startsWith("E")) &&
		    contentExists(plan, "eligibility[xml:lang=sv]") > 0) 
		    System.out.println(courseCode+": " + contentValue(plan, "eligibility[xml:lang=sv]"));
		    
		if (debug == 26 && courseCode.endsWith("X") &&
		    contentExists(plan, "goals[xml:lang=sv]") > 0) 
		    System.out.println(courseCode+": " + contentValue(plan, "goals[xml:lang=sv]"));
		    
		
		// Output course code information.
		sbCSV.append(courseCode + ";");
		
		// Get the text contents of the Swedish goals, content, eligibility and disposition elements.
		String textSwe = plan.select("goals[xml:lang=sv], content[xml:lang=sv],"
				+ "eligibility[xml:lang=sv], disposition[xml:lang=sv]").text();
		
		// Identify the language of the relevant Swedish text (if it exists).
		int languageSwe = -1;
		if (!textSwe.isEmpty()) {
			languageSwe = identifyLanguage(textSwe);
			sbCSV.append((languageSwe == LANG_SWEDISH ? "swedish" : "english") + ";");
		} else {
			sbCSV.append("NO_SWE_TEXT;");
		}
		
		// Get the text contents of the English goals, content, eligibility and disposition elements.
		String textEng = plan.select("goals[xml:lang=en], content[xml:lang=en],"
				+ "eligibility[xml:lang=en], disposition[xml:lang=en]").text();
		
		// Identify the language of the relevant English text (if it exists).
		if (!textEng.isEmpty()) {
			int language = identifyLanguage(textEng);
			sbCSV.append((language == LANG_SWEDISH ? "swedish" : "english") + ";");
		} else {
			sbCSV.append("NO_ENG_TEXT;");
		}

		if (syllabusOutput) {
		    Element enGoals = plan.select("goals[xml:lang=en]").first();
		    Element enContent = plan.select("content[xml:lang=en]").first();
		    if (enGoals != null && !enGoals.text().isEmpty()) {
			Element enName = course.select("title[xml:lang=en]").first();
			System.out.print("<h2>"+courseCode + " ");
			if (enName != null) System.out.print(enName.text());
			System.out.print("</h2>\n");
			System.out.print("<span>"+ enGoals.html()+"</span>\n");
			System.out.print("<span>");
			if (enContent != null) System.out.print(enContent.html());
			System.out.print("</span>\n");
		    }
		}
		
		// Process the goals.
		Element svGoals = plan.select("goals[xml:lang=sv]").first();
		if (svGoals != null && !svGoals.text().isEmpty()) {
			
			// If the Swedish goals are written in Swedish, perform the needed processing.
			if (languageSwe == LANG_SWEDISH) {
			        if (debug == 20 || debug == 100) System.out.println(courseCode + ":");

				// Preprocess the goals.
				String processedGoals = preprocessGoals(svGoals);
				if (debug>99) System.out.println(processedGoals);
				// Extract the verbs in each row.
				List<List<String>> rowVerbs = extractAllVerbs(processedGoals);
				
				// Get the distribution of Bloom's taxonomy verbs in each row.
				bloomsDistribution = getBloomsDistribution();
				
				// Classify the rows.
				rowTypes = classifyRows(rowVerbs, bloomsDistribution);
				
				// Create an array for the highest Bloom's class
				// and fill it with -1 initially.
				highestBloomClass = new int[bloomsDistribution.length];
				Arrays.fill(highestBloomClass, -1);
				
				// Perform further processing on each row.
				for (int i = 0; i < bloomsDistribution.length; i++) {
					
					// If the row is an ILO, increase the relevant counters.
				    if (rowTypes[i] == ROW_COMBO_ILO_HEADER) { nNormalILOs++;} else
					if (rowTypes[i] == ROW_ILO) {
						
						// Increase the (normal) ILO counter.
						nNormalILOs++;
						
						// If the previous row was a higher grade/purpose ILO or a higher grade/purpose header,
						// set this row to be a higher grade/purpose ILO and increase the corresponding counter
						// while also decreasing the counter for normal ILOs.
						if (i > 0) {
							if (rowTypes[i-1] == ROW_HIGHER_GRADE_ILO || rowTypes[i-1] == ROW_HIGHER_GRADE_HEADER) {
								rowTypes[i] = ROW_HIGHER_GRADE_ILO;
								nHigherGradeILOs++;
								nNormalILOs--;
							} else if (rowTypes[i-1] == ROW_PURPOSE_ILO || rowTypes[i-1] == ROW_PURPOSE_HEADER) {
								rowTypes[i] = ROW_PURPOSE_ILO;
								nPurposeILOs++;
								nNormalILOs--;
							}
						}
					}

					int highestBloomCl = -1;
					// Find the highest Bloom's class for all ILOs.
					for (int j = 0; j < N_BLOOM_CLASSES; j++) {
						if (bloomsDistribution[i][j] > 0) {
						    highestBloomCl = j;
						}
					}
					if (debug == 10 && rowTypes[i]==1 && highestBloomCl==-1) System.out.println(courseCode+RowToString(i));
					if (debug>99) System.out.println("Typ "+Integer.toString(rowTypes[i])+ " Högsta Bloomklass "+Integer.toString(highestBloomCl)+":"+RowToString(i));
					// Increment this ILO's highest Bloom class frequency.
					if ((rowTypes[i] == ROW_ILO || rowTypes[i] == ROW_COMBO_ILO_HEADER) && highestBloomCl != -1) {
					    highestBloomClass[i] = highestBloomCl;
					    bloomFrequency[highestBloomClass[i]] += 1;
					}
				}
			}
		}

		if (debug==199) System.out.println(course.select("subjectCode").text());


		/****************************************/
		/**                                    **/
		/** Construction of the CSV file BELOW **/
		/**                                    **/
		/****************************************/

		// "plan" content.
		sbCSV.append(contentExists(plan, "content[xml:lang=sv]") + ";");
		sbCSV.append(contentExists(plan, "goals[xml:lang=sv]") + ";");
		sbCSV.append(contentExists(plan, "goals[xml:lang=en]") + ";");
		sbCSV.append(contentExists(plan, "eligibility[xml:lang=sv]") + ";");
		sbCSV.append(contentExists(plan, "literature[xml:lang=sv]") + ";");
		sbCSV.append(contentExists(plan, "examinationComments[xml:lang=sv]") + ";");
		sbCSV.append(contentExists(plan, "requirmentsForFinalGrade[xml:lang=sv]") + ";");
		sbCSV.append(contentAttribute(plan, "coursePlan", "validFromSemester") + ";");
		sbCSV.append(contentExists(plan, "requiredEquipment[xml:lang=sv]") + ";");
		
		// "round" content.
		sbCSV.append(contentValue(round, "tutoringLanguage") + ";");
		
		// "course" content.
		sbCSV.append(contentValue(course, "educationalLevelCode") + ";");
		sbCSV.append(contentValue(course, "credits[xml:lang=en]") + ";");
		sbCSV.append(contentExists(course, "title[xml:lang=sv]") + ";");
		sbCSV.append(contentExists(course, "title[xml:lang=en]") + ";");
		sbCSV.append(contentValue(course, "gradeScaleCode") + ";");
		sbCSV.append(contentValue(course, "department") + ";");
		sbCSV.append(contentValues(course, "examiner") + ";");
		
		// Check the examination set for number of examination rounds.
		if (examinationSet.text().isEmpty()) {
			sbCSV.append("-1;");
		} else {
			Elements examRounds = examinationSet.select("examinationRound");
			
			// Find and output the examination rounds. 
			ArrayList<String> credits = new ArrayList<>();
			for (Element examRound : examRounds) {
				credits.add(examRound.select("credits[xml:lang=en]").first().text());
			}
			sbCSV.append(credits.size() + ";");
		}
		
		// Number of fields of study (course subjects).
		sbCSV.append(courseSubjects.getOrDefault(courseCode, new ArrayList<>()).size() + ";");
		
		// Find all relevant keywords.
		Map<String, Set<String>> keywords = checkForKeywords(
								     (plan.select("[xml:lang=sv]").text() + " "
								      + course.select("[xml:lang=sv]").text() + " "
								      + round.select("[xml:lang=sv]").text() + " "
								      + examinationSet.select("[xml:lang=sv]").text()).toLowerCase());

		// For sustainability, only look in ILOs and assessment.
		Map<String, Set<String>> sustainabilitykeywords;
		if (FIND_SUSTAINABILITY_KEYWORDS)
		    sustainabilitykeywords = checkForKeywords(
							      (plan.select("goals[xml:lang=sv]").text() + " "
							       + examinationSet.select("[xml:lang=sv]").text()).toLowerCase());
		    		
		// For other keywords, only look in examination comment.
		Map<String, Set<String>> otherkeywords;
		if (FIND_OTHER_KEYWORDS)
		    otherkeywords = checkForKeywords(
				plan.select("examinationComments[xml:lang=sv]").text().toLowerCase());
		    		
		// Output whether there are any ethics keywords or not.
		sbCSV.append((keywords.containsKey("ethics") ? 1 : 0) + ";");
		
		// If the flag for finding SPECIFIC keywords is set, construct the output
		// containing all keywords separated into which category they belong to.
		if (FIND_SPECIFIC_KEYWORDS) {
			if (!keywords.isEmpty()) {
			    StringBuilder SPECIFIC = new StringBuilder();
				
			    if (FIND_ECE_KEYWORDS) {
				SPECIFIC.append(";");
				// Research keywords.
				if (keywords.containsKey("research")) {
					keywords.get("research").stream().forEach(word -> SPECIFIC.append(word + ","));
					SPECIFIC.setLength(SPECIFIC.length()-1); // Remove last comma.
				}

				SPECIFIC.append(";");
				// Labor market keywords.
				if (keywords.containsKey("laborMarket")) {
					keywords.get("laborMarket").stream().forEach(word -> SPECIFIC.append(word + ","));
					SPECIFIC.setLength(SPECIFIC.length()-1); // Remove last comma.
				}

				SPECIFIC.append(";");
				// Innovation keywords.
				if (keywords.containsKey("innovation")) {
					keywords.get("innovation").stream().forEach(word -> SPECIFIC.append(word + ","));
					SPECIFIC.setLength(SPECIFIC.length()-1); // Remove last comma.
				}
			    }
			    if (FIND_SUSTAINABILITY_KEYWORDS) {
				SPECIFIC.append(";");
				// Sustainability keywords.
				if (sustainabilitykeywords.containsKey("sustainability")) {
					sustainabilitykeywords.get("sustainability").stream().forEach(word -> SPECIFIC.append(word + ","));
					SPECIFIC.setLength(SPECIFIC.length()-1); // Remove last comma.
				}
			    }
			    if (FIND_OTHER_KEYWORDS) {
				SPECIFIC.append(";");
				// Other keywords.
				if (otherkeywords.containsKey("otherkeywords")) {
					otherkeywords.get("otherkeywords").stream().forEach(word -> SPECIFIC.append(word + ","));
					SPECIFIC.setLength(SPECIFIC.length()-1); // Remove last comma.
				}
			    }
			    if (SPECIFIC.toString().replace(";","").length()>0) {
				outputSPECIFIC.append(courseCode);
				outputSPECIFIC.append(SPECIFIC);
				outputSPECIFIC.append("\n");
			    }
			}
		}
		
		// Output ILO information.
		sbCSV.append(bloomsDistribution.length + ";");	// Number of rows
		sbCSV.append(nNormalILOs + ";");				// Number of ILOs
		sbCSV.append(nHigherGradeILOs + ";");			// Number of higher grade ILOs
		sbCSV.append(nPurposeILOs + ";");				// Number of purpose ILOs
		
		// Output the ILO frequency for each Bloom's taxonomy class.
		for (int i = 0; i < N_BLOOM_CLASSES; i++) {
			sbCSV.append(bloomFrequency[i] + ";");
		}
		
		// Output the maximum Bloom's taxonomy class for any ILO in the syllabus.
		sbCSV.append(Arrays.stream(highestBloomClass).max().orElse(-1));
		
		/****************************************/
		/**                                    **/
		/** Construction of the CSV file ABOVE **/
		/**                                    **/
		/****************************************/
		
		
		
		// Add the current CSV to the output.
		outputCSV.append(sbCSV + "\n");
	}
	
	
	/**
	 * Check if the given content is non-empty.
	 * 
	 * @param baseElement The element to look in.
	 * @param name The name of the given content.
	 * @return 1 if the given content is non-empty, 0 otherwise.
	 */
	private int contentExists(Element baseElement, String name) {
		
		// Extract the specified content.
		Element content = baseElement.select(name).first();
		
		// Check if the content does not exist or is empty.
		if (content == null || content.text().isEmpty()) {
			return 0;
		} else {
			return 1;
		}
	}
	
	
	/**
	 * Check if the given content is non-empty and if so, return the content.
	 * 
	 * @param baseElement  The element to look in.
	 * @param name The name of the given content.
	 * @return The content if it is non-empty, "false" otherwise.
	 */
	private String contentValue(Element baseElement, String name) {
		
		// Extract the specified content.
		Element content = baseElement.select(name).first();
		
		// Check if the content does not exist or is empty.
		if (content == null || content.text().isEmpty()) {
			return false + "";
		} else {
			return content.text();
		}
	}
	
	
	/**
	 * Check if the given content is non-empty and if so, return a list of the content of all such elements.
	 * 
	 * @param baseElement  The element to look in.
	 * @param name The name of the given content.
	 * @return The content if it is non-empty, "false" otherwise.
	 */
	private String contentValues(Element baseElement, String name) {
		
		// Extract the specified content.
		Element content = baseElement.select(name).first();
		
		// Check if the content does not exist or is empty.
		if (content == null || content.text().isEmpty()) {
			return false + "";
		} else {
		    String values = "(" + content.text();
		    content = content.nextElementSibling();
		    while (content != null) {
			values += "," + content.text();
			content = content.nextElementSibling();
		    }
		    return values + ")";
		}
	}
	
	
	/**
	 * Check if the given content contains the given attribute and that it is non-empty.
	 * 
	 * @param baseElement  The element to look in.
	 * @param name The name of the content.
	 * @param attribute The name of the attribute.
	 * @return 1 if the given content is non-empty, 0 otherwise.
	 */
	private int contentAttribute(Element baseElement, String name, String attribute) {
		
		// Extract the specified content.
		Element content = baseElement.select(name + "[" + attribute + "]").first();
		
		// Check if the content does not exist or is empty.
		if (content == null || content.text().isEmpty()) {
			return 0;
		} else {
			return 1;
		}
	}
	
	/**
	 * Calculate the distribution of Bloom's taxonomy verbs in each row.
	 * 
	 * @return Two-dimensional array containing the distribution of
	 * each class in Bloom's taxonomy (second dimension) for each row (first dimension).
	 */
	private int[][] getBloomsDistribution() {
		
		// Contains the distribution.
		int[][] bloomsDistribution = new int[syllabusWords.size()][N_BLOOM_CLASSES];
		
		// Process each sentence.
		for (int i = 0; i < syllabusWords.size(); i++) {
			List<String> sentence = syllabusWords.get(i);
			int matchingLength;
			
			// Use a pointer which ranges over the words in the sentence.
			for (int j = 0; j < sentence.size(); j += (matchingLength == 0 ? 1 : matchingLength)) {
			    matchingLength = 0;
			    
			    for (int nWords : verbToBloom.keySet()) {
					// Compare the sentence words to all Bloom's verbs
					// and increase the corresponding counters if they match.
					for (List<String> bloomWords : verbToBloom.get(nWords).keySet()) {
					    boolean wildcard = false;
					    int noOfBloomWords = bloomWords.size();
					    int currentBloomIndex = 0;
					    for (int k = j; k < sentence.size() && currentBloomIndex < noOfBloomWords; k++) {
						if (bloomWords.get(currentBloomIndex).equals("*")) {
						    currentBloomIndex++;
						    wildcard = true;
						}
						if (bloomWords.get(currentBloomIndex).equals(sentence.get(k))) {
						    currentBloomIndex++;
						    if (currentBloomIndex == noOfBloomWords) {
							bloomsDistribution[i][verbToBloom.get(nWords).get(bloomWords)] += 1;
							matchingLength = k+1-j;
							if (debug == 20) {
							    for (int bi = 0; bi < noOfBloomWords; bi++)
								System.out.print(bloomWords.get(bi)+" ");
							    System.out.println();
							}
							break;
						    }
						    wildcard = false;
						} else if (!wildcard) break;
					    }
					}
				}
			}
		}
		
		return bloomsDistribution;
	}

    private String RowToString(int rowNo) {
	StringBuilder result = new StringBuilder();
	List<String> row = syllabusRawWords.get(rowNo);
	for (String w: row) result.append(" ").append(w);
	return result.toString();
    }

	
	/**
	 * Classify the rows according to if they are ILOs, list headers etc.
	 * 
	 * @param rowVerbs The verbs in each row.
	 * @param classDistribution The distribution of Bloom's taxonomy verbs in each row.
	 * @return An int array with the classification for each row.
	 */
	private int[] classifyRows(List<List<String>> rowVerbs, int[][] classDistribution) {
		
		// Contains the type for each row.
		int[] rowTypes = new int[syllabusWords.size()];
		
		// Classify each row separately.
		for (int i = 0; i < rowTypes.length; i++) {
			List<String> row = syllabusWords.get(i);
			List<String> verbs = rowVerbs.get(i);
			int type = ROW_OTHER;
			
			// Get the first three words if they exist (not including "att" which is the zeroth word).
			String word1 = row.size() > 1 ? row.get(1) : "";
			String word2 = row.size() > 2 ? row.get(2) : "";
			String word3 = row.size() > 3 ? row.get(3) : "";
			String lastword = row.size() > 1 ? row.get(row.size()-1) : "";

			// Classify each row depending on what words or verbs it contains.
			// This is a heuristic method that was constructed by manually
			// checking the rows and implementing fixes which correctly identify
			// the rows without destroying the identification for the other rows.
			if (row.contains("hög")
					&& (row.contains("betyg") || row.contains("betygsnivå") || row.contains("betygsgrad"))) { // Higher grade header.
				type = ROW_HIGHER_GRADE_HEADER;
			} else if (!row.contains("godkänd")
					&& (word1.equals("för") && word2.equals("att") ||
					    word2.equals("syfte") && word3.equals("att") ||
					    word1.equals("så") && word2.equals("att"))) { // Purpose header.
				type = ROW_PURPOSE_HEADER;
			} else if (row.contains(LISTCHAR) &&
				   !(word1.equals("efter") &&
				     (word2.equals("genomgången")||word2.equals("godkänd")||word2.equals("avklarad")))) { // ILO.
				type = ROW_ILO;
			} else if (!Collections.disjoint(row, ILOHeaderWords)) { // Contains ILO header words.
				
				// First, check for words usually contained in a course description (or ILO/header combo).
				// Else, if there are over 15 words in the row, it is probably an ILO/header combo.
				// Else, it is probably an ILO list header.
			        if (lastword.equals("kunna")) {
				    type = ROW_ILO_LIST_HEADER;
				} else
				if (word1.equals("kurs") || row.contains("övergripande") || row.contains("syfte") 
						|| word1.equals("denna") && word2.equals("kurs")
						|| word1.equals("kurs") && (word2.equals("syfta") || word2.equals("behandla"))) {
					if (row.contains("efter") && row.contains("kunna")) {
						type = ROW_COMBO_ILO_HEADER;
					} else {
						type = ROW_COURSE_DESCRIPTION;
					}
				} else if (row.size() > 15 && !lastword.equals("kunna")) { // Long row is probably an ILO/header combo.
					type = ROW_COMBO_ILO_HEADER;
				} else {
					type = ROW_ILO_LIST_HEADER;
				}
			} else if (row.contains("kurs")
					|| (word1.equals("denna") && word2.equals("kurs") 
					|| word1.equals("kurs") && word2.equals("syfta"))) { // Course description.
				type = ROW_COURSE_DESCRIPTION;
			} else if ((verbs.contains("kunna") && !verbs.get(0).equals("kunna")) || row.contains("mål")) { // ILO list header.
				
				// If the row contains "övergripande" or starts with "kurs" or "denna kurs",
				// it is probably a purpose header.
				// Otherwise, if it is long (>10 words), contains at least 2 verbs
				// and starts with a verb, it is probably an ILO.
				// Otherwise, it is probably a list header.
				if (row.contains("övergripande") || word1.equals("kurs") || (word1.equals("denna") && word2.equals("kurs"))) {
					type = ROW_COURSE_DESCRIPTION;
				} else if ((row.size() > 10 && verbs.size() >= 2 || Collections.disjoint(row, ILOHeaderWords))
						&& verbs.contains(row.get(0))) {
					type = ROW_ILO;
				} else {
					type = ROW_ILO_LIST_HEADER;
				}
			} else if (row.size() < 50 && (IntStream.of(classDistribution[i]).sum() > 0 || verbs.contains(row.get(1)))) {
				// If the row has less than 50 words and active verbs are used or it starts with a verb, assume it is an ILO.
				type = ROW_ILO;
			} else if (row.contains("kunskap") && row.contains("förståelse")
					|| row.contains("färdighet") && row.contains("förmåga")
					|| row.contains("värderingsförmåga") && row.contains("förhållningssätt")) {
				// Headers according to the three levels in the Higher Education Ordinance.
				type = ROW_HF_LEVELS_HEADER;
			}

			if (type == ROW_ILO && verbs.size()==0) type = ROW_ILO_NO_VERB;
			
			// Add the type of this row to the total array.
			rowTypes[i] = type;

			if (debug>99) { System.out.println("typ "+Integer.toString(type)+":"+RowToString(i)); }
		}
		
		return rowTypes;
	}
	
	
	/**
	 * Identify the language of the given goals using the method of Cavnar and Trenkle
	 * described in Section 2.4.3 and Section 3.4.1 in my thesis.
	 * 
	 * @param goals The given goals.
	 * @return The language.
	 */
	private int identifyLanguage(String text) {
		
		// Contains counters for each trigram (three characters).
		HashMap<String, Integer> trigramCounts = new HashMap<>();
		
		// Split the goals text into words.
		String[] goalsWords = text.toLowerCase().split("[\\p{Punct} ]+", 0);

		// Count the number of occurrences for each trigram in the goals words.
		for (String word : goalsWords) {
			for (int i = 0; i < word.length()-2; i++) {
				
				// Extract a trigram and increase the corresponding counter. 
				String s = word.substring(i, i+3);
				trigramCounts.put(s, trigramCounts.getOrDefault(s, 0) + 1);
			}
		}
		
		// Create a list containing the trigrams sorted by their frequency
		// in the goals text.
		ArrayList<String> trigramsFreqSorted = new ArrayList<>();
		trigramCounts.entrySet().stream()
		        .sorted(Map.Entry.<String, Integer> comparingByValue().reversed())
		        .forEach(entry -> {
		        	trigramsFreqSorted.add(entry.getKey());
		        });
		
		// The initial distances to both Swedish and English are zero.
		int totDistSwe = 0;
		int totDistEng = 0;
		
		// Calculate the distance to each language by comparing
		// the out-of-place value for each trigram.
		for (int i = 0; i < trigramsFreqSorted.size(); i++) {
			
			// Find the indexes of the trigram in the languages.
			int indexSwe = sweTopTrigrams.indexOf(trigramsFreqSorted.get(i));
			int indexEng = engTopTrigrams.indexOf(trigramsFreqSorted.get(i));
			
			// Calculate the distance (out-of-place value) for the trigram.
			// If the trigram does not exist in the language,
			// set the distance to be one more than the number of used top trigrams.
			int distanceSwe = indexSwe != -1 ? Math.abs(indexSwe-i) : sweTopTrigrams.size()+1;
			int distanceEng = indexEng != -1 ? Math.abs(indexEng-i) : engTopTrigrams.size()+1;
			
			// Add the trigram distance to the total distance.
			totDistSwe += distanceSwe;
			totDistEng += distanceEng;
		}
		
		// Choose the language with the shortest distance to the text.
		// If the distance is equal, choose Swedish.
		int chosenLanguage;
		if (totDistSwe <= totDistEng) {
			chosenLanguage = LANG_SWEDISH;
		} else {
			chosenLanguage = LANG_ENGLISH;
		}

		return chosenLanguage;
	}
	
	
	/**
	 * Perform preprocessing such as identifying the ILOs, removing strange character on the given goals.
	 * 
	 * @param goals
	 * @return
	 */
	private String preprocessGoals(Element goals) {
		StringBuilder sb = new StringBuilder();
		
		if (debug==5) System.out.println(goals.html());
		// Process lists containing <ul>, <ol> or <p> tags.
		for (Element e : goals.children()) {
			if (e.is("ul, ol")) {
				for (Element li : e.select("li")) {
					String text = li.html();
					// Replace punctuation and spaces in the end with a dot.
					text = text.replaceAll("\\p{Punct}+(&nbsp;| )*$", "").concat(".");
					
					// Remove ending "etc." or "osv." since they cause sentences
					// to be erroneously merged in Granska.
					text = text.replaceAll(" (etc|osv)\\p{Punct}$", ".");
					
					// Append the processed text.
					sb.append(LISTCHAR+"Att " + text + "\r\n");
				}
			} else if (e.is("p")) {
				String text = e.html();
				
				// Replace punctuation and spaces in the end with a dot.
				text = text.replaceAll("\\p{Punct}+(&nbsp;| )*$", "").concat(".");
				
				// Remove ending "etc." or "osv." since they cause sentences
				// to be erroneously merged in Granska.
				text = text.replaceAll(" (etc|osv)\\p{Punct}$", ".");
				
				// Check if this <p> starts with a punctuation and thus represents a goal (probably).
				if (text.matches("^(&nbsp;| )*(\\w*[-\\])*.]|\\d |o |•|·|·|●|─|̶)(&nbsp;| )*.*$")) {
					
					// Replace the punctuation with a "¢" to denote a list item.
					// If it starts with a <br> tag, also add CR+LF.
					text = text.replaceAll("^(&nbsp;| )*(\\w*[-\\])*.]|\\d |o |•|·|·|●|─|̶)(&nbsp;| )*", LISTCHAR)
							   .replaceAll("<br[ /]*>(&nbsp;| )*(\\w*[-\\])*.]|\\d |o |•|·|·|●|─|̶)", ".\r\n¢att ")
							   .replaceAll("\\.\\.", "."); // Replace many dots with only one
				}
				
				// Append the processed text.
				if (text.substring(0,1).equals(LISTCHAR))
				    sb.append(LISTCHAR+"Att " + text.substring(1) + "\r\n");
				else
				    sb.append("Att " + text + "\r\n");
			}
		}
		
		// If there are no tags but only text, simply add the whole text. 
		if (goals.children().isEmpty()) {
			sb.append("Att " + goals.text() + "\n");
		}

		// Replace various patterns and return the result.
		return sb.toString()
				.replaceAll("å", "å").replaceAll("ä", "ä").replaceAll("ö", "ö") // Convert weird two-piece åäö (e.g. a¨) to normal åäö
				.replaceAll("\\p{Punct}*<br[ /]*>(\\w*[-\\])*.]|\\d |o |•|·|·|●|─|̶)", ".\r\n¢¢att ") // Format nested lists using "¢¢" as bullet
				.replaceAll("<br[ /]*>", ".\r\nAtt ") // Convert HTML line break to LF/CR
				.replaceAll("- ", " ") // Remove the hyphen which starts some subgoals
				.replaceAll("&nbsp;?", " ") // Convert nbsp to normal space
				.replaceAll("&amp;", "&") // Convert "&amp;" to "&"
				.replaceAll("", "") // Remove control character ()
				.replaceAll("[^\\p{InBasic_Latin}\\p{InLatin-1Supplement}]", "") // Remove non-ISO-8859-1 chars
				.replaceAll("(\\p{Punct}gt;|­)", "") // Remove remains of HTML ">" and soft hyphens
				.replaceAll("(<\\p{Alnum}+>|</\\p{Alnum}+>?)", "") // Remove remains of HTML tags
				.replaceAll("\\.\\.+", ".") // Replace many dots with only one
				.replaceAll("\r\n(([aA]tt| |¢)*[.\\p{Punct} ]*\r\n)+", "\r\n") // Remove rows with only "¢", "att" and punctuation/spaces
				.replaceAll(":", ""); // Remove colon since e.g. "SDN:er" causes problem in Granska 
	}
	
	
	/**
	 * Connect to Granska and extract all verbs from the given goals string.
	 * 
	 * @param goals The given goals string.
	 * @return A list containing 
	 * @throws MalformedURLException
	 * @throws IOException
	 * @throws InterruptedException
	 */
	private List<List<String>> extractAllVerbs(String goals) throws MalformedURLException, IOException, InterruptedException {
		
		// Contains all verbs separated by the rows (the inner lists) in which they occur.
		List<List<String>> syllabusVerbs;
		
		// Try to extract the verbs.
		// If the extraction fails, repeat the whole process since it might be due
		// to Granska crashing for a short time (does not happen often though).
		boolean finished = false;
		do {
			syllabusVerbs = new ArrayList<>();
			
			// Encode and build the query URL.
			String query = URLEncoder.encode(goals, "ISO-8859-1");
			String url = "http://skrutten.nada.kth.se/scrut.php?ruleset=svesve&text=" + query + "&xmlout=on&x=Granska";
			
			// Send the query to Granska and parse the results.
			// If the request fails, try again in 5 seconds.
			Document origGranska = null; 
			while (origGranska == null) {
				try {
					origGranska = Jsoup.parse(new URL(url).openStream(), "ISO-8859-1", url);
				} catch (Exception e) {
					e.printStackTrace();
					Thread.sleep(5000);
				}
			}
			
			// Unescape entities in the Granska response and parse it.
			Element granska = Jsoup.parse(unescapeEntities(origGranska));
			
			// Extract all sentences.
			Elements sentences = granska.select("root > s");
			
			// Process each sentence.
			for (Element sentence : sentences) {
				
				// Extract the text from the sentence.
				String text = sentence.select("text").text();
				
				// Used to indicate if the sentence is new
				// or if it is a continuation of the previous sentence.
				boolean newSentence = false;
				
				// Contains the words and verbs in this sentence.
				List<String> sentenceWords;
				List<String> sentenceRawWords;
				List<String> sentenceVerbs;
				
				// If the sentence does not start with "Att " or "¢" it is probably a continuation
				// of the previous sentence so continue using the previous lists.
				// Otherwise, it is a new sentence so create new lists.
				if (!text.startsWith("Att ") && !text.startsWith(LISTCHAR)) {
					sentenceWords = syllabusWords.get(syllabusWords.size()-1);
					sentenceRawWords = syllabusWords.get(syllabusRawWords.size()-1);
					sentenceVerbs = syllabusVerbs.get(syllabusVerbs.size()-1);
				} else { 
					sentenceWords = new ArrayList<>();
					sentenceRawWords = new ArrayList<>();
					sentenceVerbs = new ArrayList<>();
					newSentence = true;
				}

				// Add the lemma of each word to the total list of words
				// and also to the total list of verbs if it is a verb.
				for (Element word : sentence.select("w")) {
					
					// If the word is just punctuation, do not add it.
					if (word.text().matches("^\\p{Punct}$")) {
						continue;
					}
					
					// Get the lemma of the word.
					String lemma = word.attr("lemma");
					
					// Add the lemma to the total list of words.
					sentenceWords.add(lemma);
					sentenceRawWords.add(word.text());
					
					// Add the lemma to the total list of verbs if it is a verb.
					int wordTag = Integer.parseInt(word.attr("tag")); 
					if (VERB_TAGS_GRANSKA.contains(wordTag)) {
						sentenceVerbs.add(lemma);
					}
				}

				if (correctSpelling) {
				
				// Extract grammar errors suggested by Granska.
				Elements gramErrors = granska.select("s[ref=" + sentence.attr("ref") + "] > gramerrors > gramerror");
				
				// Correct the grammar errors that are spelling errors.
				for (Element gramError : gramErrors) {
					
					// Extract which rule the grammar error violates.
					Element rule = gramError.select("rule").first();
					
					// Find any spelling error rules.
					if (rule.text().equals("stav1@stavning")) {
						
						// Extract the old word and the new suggestion.
						String oldWord = gramError.select("marked > emph").text();
						Element newWordElem = gramError.select("suggestions > sugg").first();
						
						// If there are any suggestions, use the first one to replace the old word.
						// Otherwise, keep the old word as it is.
						if (newWordElem != null) {
							
							// Split the new suggestion into the constituent words.
							// Usually, the suggestion is just one word.
							String[] newWords = newWordElem.text().split(" ");
							
							// Replace all occurrences of the old word with the new suggestion.
							Collections.replaceAll(sentenceWords, oldWord, newWords[0]);
							Collections.replaceAll(sentenceVerbs, oldWord, newWords[0]);
							
							// If Granska separated the word into several words,
							// append the rest of the words to the end of the sentence.
							// This will destroy the original word order of the sentence,
							// but it does not matter for later classification and analysis.
							for (int i = 1; i < newWords.length; i++) {
								sentenceWords.add(newWords[i]);
								sentenceVerbs.add(newWords[i]);
							}
						}
					}
				}
				
				// If the processed sentence is new, add its content to the total lists.
				if (newSentence) {
					syllabusWords.add(sentenceWords);
					syllabusRawWords.add(sentenceRawWords);
					syllabusVerbs.add(sentenceVerbs);
				}
			      }
			}
			
			// If allWords is empty, Granska probably crashed so try again in 5 seconds.
			if (!syllabusWords.isEmpty()) {
				finished = true;
			} else {
				Thread.sleep(5000);
			}
		} while (!finished);
		
		// Add the words and verbs from this syllabus to the total sets.
		syllabusWords.stream().forEach(list -> {
			list.stream().forEach(word -> allWordsTotal.add(word));
		});
		syllabusVerbs.stream().forEach(list -> {
			list.stream().forEach(verb -> allVerbsTotal.add(verb));
		});
		
		return syllabusVerbs;
	}
	
	/**
	 * Search in the given text for certain keywords.
	 * 
	 * @param text The given text.
	 * @return Occurrences of keywords in each category.
	 */
	private Map<String, Set<String>> checkForKeywords(String text) {
		
		// Maps each keyword category to all words which contain one of the category keywords. 
		Map<String, Set<String>> occurrences = new HashMap<>();
		
		// Split the string into words.
		String[] words = text.split("\\p{Punct}*[\\s ]+\\p{Punct}*");
		
		// Look for keyword matches in each word and add matching words to the map.
		for (String word : words) {
			
			// If the word contains "http" it is probably an URL so skip it.
			if (word.contains("http")) {
				continue;
			}
			
			// Ethics keywords.
			for (String keyword : ethicsKeywords) {
				if (word.contains(keyword)) {
					if (occurrences.containsKey("ethics")) {
						occurrences.get("ethics").add(word);
					} else {
						Set<String> temp = new HashSet<>();
						temp.add(word);
						occurrences.put("ethics", temp);
					}
				}
			}
			
			// If the flag for finding SPECIFIC keywords is set,
			// search for the relevant keywords.
			if (FIND_SPECIFIC_KEYWORDS) {
			    if (FIND_ECE_KEYWORDS) {
				// Research keywords.
				for (String keyword : researchKeywords) {
					if (word.contains(keyword)) {
						if (occurrences.containsKey("research")) {
							occurrences.get("research").add(word);
						} else {
							Set<String> temp = new HashSet<>();
							temp.add(word);
							occurrences.put("research", temp);
						}
					}
				}
				
				// Labor market keywords.
				for (String keyword : laborMarketKeywords) {
					if (word.contains(keyword)) {
						if (occurrences.containsKey("laborMarket")) {
							occurrences.get("laborMarket").add(word);
						} else {
							Set<String> temp = new HashSet<>();
							temp.add(word);
							occurrences.put("laborMarket", temp);
						}
					}
				}
				
				// Innovation keywords.
				for (String keyword : innovationKeywords) {
					if (word.contains(keyword)) {
						if (occurrences.containsKey("innovation")) {
							occurrences.get("innovation").add(word);
						} else {
							Set<String> temp = new HashSet<>();
							temp.add(word);
							occurrences.put("innovation", temp);
						}
					}
				}
			    }
			    if (FIND_SUSTAINABILITY_KEYWORDS) {
				// Sustainability keywords.
				for (String keyword : sustainabilityKeywords) {
					if (word.startsWith(keyword)) {
						if (occurrences.containsKey("sustainability")) {
							occurrences.get("sustainability").add(word);
						} else {
							Set<String> temp = new HashSet<>();
							temp.add(word);
							occurrences.put("sustainability", temp);
						}
					}
				}
			    }

			    if (FIND_OTHER_KEYWORDS) {
				// Other keywords.
				for (String keyword : otherKeywords) {
					if (word.startsWith(keyword)) {
						if (occurrences.containsKey("otherkeywords")) {
							occurrences.get("otherkeywords").add(word);
						} else {
							Set<String> temp = new HashSet<>();
							temp.add(word);
							occurrences.put("otherkeywords", temp);
						}
					}
				}
			    }
			}
		}
		
		return occurrences;
	}

	
	/**
	 * Load the verbs classified in Bloom's taxonomy from all specified files.
	 * The verbs are separated depending on the number of words they contain.
	 */
	private void loadBloomVerbs() throws IOException {
		
		// Check each specified path for verbs.
		for (String path : BLOOM_VERBS_PATHS) {
			
			// Read the lines from file.
			List<String> lines = Files.readAllLines(Paths.get(path));
			
			// Initalize the Bloom's class to the highest one.
			// Note that zero indexing is used so we need to subtract one.
			int bloomClass = N_BLOOM_CLASSES - 1;
			
			// Reverse the order of the lines. This will ensure that the lowest class
			// will always be used if the verb is classified as several classes
			// since the previous entry is overwritten.
			Collections.reverse(lines);
			
			// Process each line.
			for (String line : lines) {
				
				// If the line starts with "---" it is a separator line
				// so just decrease the Bloom's class and continue to the next line.
				// Otherwise, process the line.
				if (line.startsWith("---")) {
					bloomClass--;
				} else if (!line.startsWith("(") && !line.startsWith("#")) {
					// Tokenize the line.
					List<String> verbs = Arrays.asList(line.split(" "));
					
					// If no map exists for the correct number of words, add a new one.
					verbToBloom.putIfAbsent(verbs.size(), new HashMap<>());

					// Add the verb(s) to the map.
					verbToBloom.get(verbs.size()).put(verbs, bloomClass);
				}
			}
		}
	}
	
	
	/**
	 * Unescape XML and HTML entities from the given node and return the resulting string.
	 * 
	 * @param n The given node.
	 * @return The unescaped string.
	 */
	private String unescapeEntities(Node n) {
		String result = n.toString();
		String temp;
		
		// Unescape the string until there are no differences between two iterations.
		// This is needed since entities are escaped multiple times in some syllabuses. 
		do {
			temp = result;
			result = StringEscapeUtils.unescapeHtml4(StringEscapeUtils.unescapeXml(temp));
		} while (!result.equals(temp));
		
		return result;
	}
	

	public static void main(String[] args) throws IOException, InterruptedException {

		// If no arguments (or the -help flag) is given, write usage information.
		// Otherwise, parse the arguments.
		if (args.length == 0 || args.length >= 1 && args[0].equals("-help")) {
			System.out.println("Usage: GetSyllabus [-a] [-cc <CODE>] [-ct <SEMESTER>] [-o <FILE_NAME>] [-r] [-d <level>]");
			System.out.println("Flags: -a              Classify all courses.");
			System.out.println("       -s              Output the syllabus (code, name, ILOs, contents).");
			System.out.println("       -cc <CODE>      Course code (six alphanumeric characters).");
			System.out.println("       -ct <SEMESTER>      Course year/semester in the format YYYY:T (e.g. 2016:1). Default is " + defaultSemester);
			System.out.println("       -o <FILE_NAME>  Output file name (default is \"output.csv\").");
			System.out.println("       -r <FILE_NAME>  Run ResultsCreator after the classification");
			System.out.println("                       and save the results to the given file name.");
			System.out.println("       -d <level>      Set debug level, for example 10, 20, 100.");
			System.out.println("Note: EITHER -a OR -cc must be used (not both).");
		} else {
			boolean handleAllCourses = false;
			String courseCode = "";
			String courseSemester = defaultSemester;
			boolean fullYear = true;
			String outputFileName = "raw.csv";
			String resultsOutputFileName = "";
			
			// Check each argument.
			for (int i = 0; i < args.length; i++) {
				switch (args[i]) {
				case "-a":
					handleAllCourses = true;
					break;
				case "-s":
					syllabusOutput = true;
					break;
				case "-cc":
					// Check that the argument contains six alphanumeric characters.
					if (i+1 < args.length && args[i+1].matches("^\\p{Alnum}{6}$")) {
						courseCode = args[i+1];
					} else {
						System.err.println("ERROR: -cc must be six alphanumeric characters! (Run with -help for usage info)");
						System.exit(1);
					}
					break;	
				case "-cy":
					// Check that the argument is in the format DDDD:D where D is a digit.
					if (i+1 < args.length && args[i+1].matches("^\\d{4}:\\d$")) {
						courseSemester = args[i+1];
						fullYear = true;
					} else {
						System.err.println("ERROR: -ct must be in the format YYYY:T (e.g. 2016:1)! (Run with -help for usage info)");
						System.exit(1);
					}
					break;
				case "-ct":
					// Check that the argument is in the format DDDD:D where D is a digit.
					if (i+1 < args.length && args[i+1].matches("^\\d{4}:\\d$")) {
						courseSemester = args[i+1];
						fullYear = false;
					} else {
						System.err.println("ERROR: -ct must be in the format YYYY:T (e.g. 2016:1)! (Run with -help for usage info)");
						System.exit(1);
					}
					break;
				case "-d":
					// Check that the argument is a number.
					if (i+1 < args.length && args[i+1].matches("^[0-9]*$")) {
					    debug = Integer.parseInt(args[i+1]);
					} else {
						System.err.println("ERROR: -d must be in the format number! (Run with -help for usage info)");
						System.exit(1);
					}
					break;
				case "-o":
					// Check that the argument does not start with a dash (another flag).
					if (i+1 < args.length && !args[i+1].startsWith("-")) {
						outputFileName = args[i+1];
					} else {
						System.err.println("ERROR: Invalid path for -o flag! (Run with -help for usage info)");
						System.exit(1);
					}
					break;
				case "-r":
					// Check that the argument does not start with a dash (another flag).
					if (i+1 < args.length && !args[i+1].startsWith("-")) {
						resultsOutputFileName = args[i+1];
					} else {
						System.err.println("ERROR: Invalid path for -r flag! (Run with -help for usage info)");
						System.exit(1);
					}
					break;
				}
			}

			// If EITHER the -a flag OR -cc (AND -ct) flags were given (not both), start the classification.
			if (handleAllCourses && courseCode.isEmpty()
					|| !handleAllCourses && !courseCode.isEmpty() && !courseSemester.isEmpty()) {
			    new GetSyllabus(handleAllCourses, courseCode, courseSemester, fullYear, outputFileName);
				
				// If the -r flag is specified, run ResultsCreator after the classification.
				if (!resultsOutputFileName.isEmpty()) {
					new ResultsCreator(outputFileName, resultsOutputFileName);
				}
			} else {
				System.err.println("ERROR: Either -a OR -cc must be used (not both)! (Run with -help for usage info)");
				System.exit(1);
			}
		}
	}
}
